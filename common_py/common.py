import asyncio
import csv
import logging
import time
import zipfile
from copy import deepcopy
from io import BytesIO
from typing import List
from copy import deepcopy
import aiofiles
import aiohttp
import ujson
from cachetools import LRUCache
from sqlalchemy.future import select
from fastapi import Request
from typing import Any
from utility.config import TIMEOUT, AIRCRAFT_JSON, URL_OPEN, DB_OPEN_DIR, DB_OPEN_ZIP, DB_OPEN, URL_READSB, UNIX_SOCKET, \
    UNIX, FREQUENZA_AGGIORNAMENTO_AEREI
from utility.model import Aereo, Ricevitore, SessionLocal, SessionData
from utility.type_hint import AircraftDataRaw, DbDizionario, AircraftsJson

aircraft_cache = LRUCache(maxsize=100000000)

logger = logging.getLogger("common")


def unzip_data(data):
    with BytesIO(data) as bio, zipfile.ZipFile(bio) as zip_file:
        zip_file.extractall(DB_OPEN_DIR)


def flash(request: Request, message: Any) -> None:
    session: SessionData = request.state.session
    session.message = message


def get_flashed_message(request: Request):
    session: SessionData = request.state.session
    message = deepcopy(session.message)
    session.message = ""
    return message


class QueryUpdater:
    def __init__(self):
        self.reader: asyncio.StreamReader
        self.writer: asyncio.StreamWriter
        self.icao_presenti_nel_db: List = []  # elenco icao di cui abbiamo salvato informazioni nel nostro db
        self.data: AircraftsJson | {} = {}  # aircrafts.json
        self.aircrafts: List[AircraftDataRaw] = []  # aircrafts di aircrafts.json
        self.aircrafts_raw: List[AircraftDataRaw] = []  # aircrafts di aircrafts.json
        self.database_open: dict[str:DbDizionario] = {}  # database opensky
        self.reports: List = []
        self.aircrafts_da_servire: List[int, dict, bool] = [0, {},
                                                            False]  # timestamp, aircrafts con info, in esecuzione
        self.ricevitori: List[Ricevitore] = []

    async def get_icao_from_db(self):
        async with SessionLocal() as session_db:
            quer = await session_db.execute(select(Aereo))
            icao_list = [aereo.icao for aereo in quer.scalars().all()]
        self.icao_presenti_nel_db = icao_list

    async def fetch_data_from_url(self, logger: logging.Logger, url: str, session) -> dict:
        async with session.get(url, timeout=TIMEOUT) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {}

    async def real_update_query(self):
        if UNIX:
            data = ujson.loads(await self.fetch_data_from_unix())
        else:
            async with aiohttp.ClientSession() as session:
                data = await self.fetch_data_from_url(logger, URL_READSB, session)

        if data:
            logger.debug("using readsb")
            self.data = data
            self.aircrafts = deepcopy(self.data["aircraft"])
            self.aircrafts_raw = self.data["aircraft"]

            logger.debug("Readsb webser Online, using it")
        else:
            logger.debug("using aircrafts.json")
            async with aiofiles.open(AIRCRAFT_JSON, 'r') as file:
                content = await file.read()
                self.data = ujson.loads(content)
                self.aircrafts = deepcopy(self.data["aircraft"])
                self.aircrafts_raw = self.data["aircraft"]

            logger.info("used aircrafts.json")

    async def aicrafts_filtered_by_my_receiver(self, session, my=False):
        filtered_aircrafts = []
        ricevitore: Ricevitore = session.ricevitore
        if my:
            aircrafts = self.aircrafts_raw
        else:
            aircrafts = self.aircrafts
        for aircraft in aircrafts:
            if "recentReceiverIds" in aircraft and ricevitore.uuid[:18] in aircraft["recentReceiverIds"]:
                filtered_aircrafts.append(aircraft)
        return filtered_aircrafts

    async def update_query(self, first=False):
        logger.info("Update query in partenza!")
        if first:
            if UNIX:
                self.reader, self.writer = await asyncio.open_unix_connection(UNIX_SOCKET)
            await self.real_update_query()
            if UNIX:
                self.writer.close()
                await self.writer.wait_closed()
            return
        else:
            if UNIX:
                self.reader, self.writer = await asyncio.open_unix_connection(UNIX_SOCKET)
            while True:
                await self.real_update_query()
                await asyncio.sleep(FREQUENZA_AGGIORNAMENTO_AEREI)

    async def download_file(self, url: str, destination: str) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(destination, 'wb') as file:
                        await file.write(await response.read())
                else:
                    raise Exception(f"Unable to download the file. Status: {response.status}")

    async def unzip_db(self):
        async with aiofiles.open(DB_OPEN_ZIP, 'rb') as file:
            data = await file.read()  # Leggi tutto il file asincronamente

        # Esegui l'unzipping in un thread separato
        await asyncio.to_thread(unzip_data, data)

    async def fetch_data_from_unix(self):
        # Scrivi un messaggio al socket UNIX
        self.writer.write(b'?all')
        await self.writer.drain()

        # Leggi la risposta dal socket UNIX
        data = await self.reader.read(-1)

        return data.decode()

    async def update_db(self):
        logger.info("Estrazione database tar1090...")

        await self.get_icao_from_db()

        logger.info("Aerei recuperati!...")

        await self.download_file(URL_OPEN, DB_OPEN_ZIP)

        await self.unzip_db()
        async with aiofiles.open(DB_OPEN, mode='r') as db_file:
            content = await db_file.read()
            reader: csv.DictReader = csv.DictReader(content.splitlines())
            for riga in reader:
                icao24 = riga['icao24'].upper()
                self.database_open[icao24] = DbDizionario(riga)


query_updater = QueryUpdater()
