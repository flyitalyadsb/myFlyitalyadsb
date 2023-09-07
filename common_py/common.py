import asyncio
import csv
import logging
import zipfile
from copy import deepcopy
from io import BytesIO
from typing import Any
from typing import List

import aiofiles
import aiohttp
import ujson
from cachetools import LRUCache
from fastapi import Request
from sqlalchemy.future import select

from utility.config import TIMEOUT, AIRCRAFT_JSON, URL_OPEN, DB_OPEN_DIR, DB_OPEN_ZIP, DB_OPEN, URL_READSB, UNIX_SOCKET, \
    UNIX, AIRCRAFT_UPDATE_FREQUENCY
from utility.model import Aircraft, Receiver, SessionLocal, SessionData
from utility.type_hint import AircraftDataRaw, DatabaseDict, AircraftsJson

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


async def unzip_db():
    async with aiofiles.open(DB_OPEN_ZIP, 'rb') as file:
        data = await file.read()
    await asyncio.to_thread(unzip_data, data)


async def download_file(url: str, destination: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(destination, 'wb') as file:
                    await file.write(await response.read())
            else:
                raise Exception(f"Unable to download the file. Status: {response.status}")


async def fetch_data_from_url(logger: logging.Logger, url: str, session) -> dict:
    async with session.get(url, timeout=TIMEOUT) as response:
        if response.status == 200:
            return await response.json()
        else:
            return {}


class QueryUpdater:
    def __init__(self):
        self.reader: asyncio.StreamReader
        self.writer: asyncio.StreamWriter
        self.icao_in_database: List = []  # elenco icao di cui abbiamo salvato informazioni nel nostro db
        self.data: AircraftsJson | {} = {}  # aircraft.json
        self.aircraft: List[AircraftDataRaw] = []  # aircraft.json' aircraft that is handled in the program
        self.aircraft_raw: List[AircraftDataRaw] = []  # aircraft.json' aircraft that is not touched
        self.database_open: dict[str:DatabaseDict] = {}  # database opensky
        self.reports: List = []
        self.aircraft_to_be_served: List[float, dict, bool] = [0, {},
                                                               False]  # timestamp, aircrafts with info, in execution

    async def get_icao_from_db(self):
        async with SessionLocal() as session_db:
            quer = await session_db.execute(select(Aircraft))
            icao_list = [aircraft.icao for aircraft in quer.scalars().all()]
        self.icao_in_database = icao_list

    async def real_update_query(self):
        if UNIX:
            data = ujson.loads(await self.fetch_data_from_unix())
        else:
            async with aiohttp.ClientSession() as session:
                data = await fetch_data_from_url(logger, URL_READSB, session)

        if data:
            logger.debug("using readsb")
            self.data = data
            self.aircraft = deepcopy(self.data["aircraft"])
            self.aircraft_raw = self.data["aircraft"]

            logger.debug("Readsb webserver Online, using it")
        else:
            logger.debug("using aircraft.json")
            async with aiofiles.open(AIRCRAFT_JSON, 'r') as file:
                content = await file.read()
                self.data = ujson.loads(content)
                self.aircraft = deepcopy(self.data["aircraft"])
                self.aircraft_raw = self.data["aircraft"]

            logger.info("used aircraft.json")

    async def aicrafts_filtered_by_my_receiver(self, session, my=False):
        filtered_aircrafts = []
        ricevitore: Receiver = session.receiver
        if my:
            aircrafts = self.aircraft_raw
        else:
            aircrafts = self.aircraft
        for aircraft in aircrafts:
            if "recentReceiverIds" in aircraft and ricevitore.uuid[:18] in aircraft["recentReceiverIds"]:
                filtered_aircrafts.append(aircraft)
        return filtered_aircrafts

    async def update_query(self, first=False):
        logger.info("Starting update query!")
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
                await asyncio.sleep(AIRCRAFT_UPDATE_FREQUENCY)

    async def fetch_data_from_unix(self):
        # todo da sistemare
        await self.writer.drain()

        data = await self.reader.read(-1)

        return data.decode()

    async def update_db(self):
        logger.info("Extracting tar1090's database ...")

        await self.get_icao_from_db()

        logger.info("Aircraft loaded!...")

        await download_file(URL_OPEN, DB_OPEN_ZIP)

        await unzip_db()
        async with aiofiles.open(DB_OPEN, mode='r') as db_file:
            content = await db_file.read()
            reader: csv.DictReader = csv.DictReader(content.splitlines())
            for row in reader:
                icao24 = row['icao24'].upper()
                self.database_open[icao24] = DatabaseDict(row)


query_updater: QueryUpdater = QueryUpdater()
