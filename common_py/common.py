import asyncio
import csv
import logging
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any
from typing import List

import aiofiles
import aiohttp
import orjson
from cachetools import LRUCache
from fastapi import Request
from sqlalchemy.future import select

from utility.config import config
from utility.model import Aircraft, Receiver, SessionLocal, SessionData
from utility.type_hint import AircraftDataRaw, DatabaseDict, AircraftsJson

aircraft_cache = LRUCache(maxsize=100000000)

logger = logging.getLogger("common")


def unzip_data(data):
    with BytesIO(data) as bio, zipfile.ZipFile(bio) as zip_file:
        zip_file.extractall(config.db_open_dir)


def flash(request: Request, message: Any) -> None:
    session: SessionData = request.state.session
    session.message = message


def get_flashed_message(request: Request):
    session: SessionData = request.state.session
    message = deepcopy(session.message)
    session.message = ""
    return message


async def unzip_db():
    async with aiofiles.open(config.db_open_zip, 'rb') as file:
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


async def fetch_data_from_url(url: str, session) -> dict:
    try:
        async with session.get(url, timeout=config.timeout) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {}
    except TimeoutError as e:
        logger.error(f"Timeout error while fetching data from {url}")
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
                                                               False]  # timestamp, aircraft with info, in execution

    async def get_icao_from_db(self):
        async with SessionLocal() as session_db:
            quer = await session_db.execute(select(Aircraft))
            icao_list = [aircraft.icao for aircraft in quer.scalars().all()]
        self.icao_in_database = icao_list

    async def real_update_query(self):
        if config.unix:
            data = await self.fetch_data_from_unix()
        else:
            async with aiohttp.ClientSession() as session:
                data = await fetch_data_from_url(config.url_readsb, session)

        if data != {}:
            logger.debug("using readsb")
            self.data = data
            self.aircraft = deepcopy(self.data["aircraft"])
            print(len(self.aircraft))
            self.aircraft_raw = self.data["aircraft"]

            logger.debug("Readsb webserver Online, using it")
        else:
            logger.info("using aircraft.json")
            async with aiofiles.open(config.aircraft_json, 'r') as file:
                content = await file.read()
                self.data = orjson.loads(content)
                self.aircraft = deepcopy(self.data["aircraft"])
                self.aircraft_raw = self.data["aircraft"]

            logger.debug("used aircraft.json")

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
            Path(config.db_open_dir).mkdir(parents=True, exist_ok=True)
            if config.unix:
                self.reader, self.writer = await asyncio.open_unix_connection(config.unix_socket)
            await self.real_update_query()
            if config.unix:
                self.writer.close()
                await self.writer.wait_closed()
            return
        else:
            if config.unix:
                self.reader, self.writer = await asyncio.open_unix_connection(config.unix_socket)
            while True:
                await self.real_update_query()
                await asyncio.sleep(config.aircraft_update)

    async def fetch_data_from_unix(self):
        # Send an HTTP GET request
        request = "GET /?all HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
        self.writer.write(request.encode())
        await self.writer.drain()

        # Read the headers
        headers_buffer = bytearray()
        while True:
            chunk = await self.reader.read(4096)  # Read in chunks of 4 KB
            if not chunk:
                return {}

            headers_buffer.extend(chunk)
            if b"\r\n\r\n" in headers_buffer:
                break

        headers_data = headers_buffer.decode()

        if "\r\n\r\n" not in headers_data:
            return {}

        headers, body_start = headers_data.split("\r\n\r\n", 1)

        # Extract Content-Length value from headers
        content_length = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    return {}
                break

        if content_length is None:
            return {}

        # Read the body based on content_length
        body_buffer = bytearray(body_start.encode())
        bytes_to_read = content_length - len(body_buffer)

        while bytes_to_read > 0:
            chunk = await self.reader.read(min(bytes_to_read, 4096))
            if not chunk:
                return {}
            body_buffer.extend(chunk)
            bytes_to_read -= len(chunk)

        body = body_buffer.decode()

        try:
            data = orjson.loads(body)
            return data
        except orjson.JSONDecodeError:
            return {}

    async def update_db(self):
        logger.info("Extracting tar1090's database ...")

        await self.get_icao_from_db()

        logger.info("Aircraft loaded!...")

        await download_file(config.url_open, config.db_open_zip)

        await unzip_db()
        async with aiofiles.open(config.db_open, mode='r') as db_file:
            content = await db_file.read()
            reader: csv.DictReader = csv.DictReader(content.splitlines())
            for row in reader:
                icao24 = row['icao24'].upper()
                self.database_open[icao24] = DatabaseDict(row)


query_updater: QueryUpdater = QueryUpdater()


def print_result(result):
    print(result)
