import asyncio
import atexit
import cProfile
import logging
import os
import platform
import traceback

import aiomonitor
import psutil
import uvicorn

from common_py.common import query_updater, print_result
from modules.add_to_db.add_to_db import add_aircrafts_to_db
from modules.clients.clients import clients
from modules.remove_unused.remove_unused import remove_unused
from utility.config import config
from utility.model import SessionLocal, setup_database

logger = logging.getLogger("MAIN")
handler = logging.StreamHandler()
logger.addHandler(handler)

result = ""
atexit.register(print_result, result)


async def fastapi_start():
    configuration = uvicorn.Config("modules.app.app:app", host=config.host, port=config.port, loop="auto")
    server = uvicorn.Server(configuration)
    await server.serve()


async def sync_clients_and_db():
    session_client = SessionLocal()
    session_db = SessionLocal()

    logger.info("Starting Aircraft_DB and Clients!")
    while True:
        try:
            await add_aircrafts_to_db(session_db)
        finally:
            pass
            traceback.print_exc()
        try:
            await clients(session_client)
        finally:
            pass
            traceback.print_exc()
        await asyncio.sleep(config.clients_and_db_update)


def monitor_usage(interval=30):
    pid = os.getpid()
    process = psutil.Process(pid)

    # Calcola l'utilizzo della memoria e della CPU
    memory_use = process.memory_info().rss  # in bytes
    cpu_use = process.cpu_percent(interval=1)

    print(f"Memory Usage: {memory_use / (1024 * 1024):.2f} MB, CPU Usage: {cpu_use}%")


async def run():
    logger.info("Starting...")
    global result
    asyncio.get_event_loop().set_debug(False)
    await setup_database()
    if config.asyncio_debug:
        asyncio.get_event_loop().set_debug(True)
        m = aiomonitor.start_monitor(asyncio.get_running_loop())

    if config.debug:
        # profiler = cProfile.Profile()
        # profiler.enable()
        # asyncio.get_event_loop().set_debug(True)
        m = aiomonitor.start_monitor(asyncio.get_running_loop())
        await asyncio.gather(query_updater.update_query(True), query_updater.update_db())
        session = SessionLocal()
        await add_aircrafts_to_db(session)
        await clients(session)
        # profiler.disable()
        # profiler.print_stats(sort='cumulative')
        return

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logger.info("Downloading opensky aircraft info database and updating aircraft ")
    await asyncio.gather(query_updater.update_query(True), query_updater.update_db())

    logger.info("Starting all...")

    result = await asyncio.gather(
        sync_clients_and_db(),
        query_updater.update_query(),
        # remove_unused(),
        fastapi_start())
    print(result)


asyncio.run(run())
