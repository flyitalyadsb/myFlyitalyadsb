import asyncio
import atexit
import logging
import platform
import uvicorn

from common_py.common import query_updater, print_result
from modules.add_to_db.add_to_db import add_aircrafts_to_db

from modules.clients.clients import clients
from utility.config import config
from utility.model import SessionLocal, setup_database

logger = logging.getLogger("MAIN")

result = ""
atexit.register(print_result, result)


def fastapi_start():
    uvicorn.run("modules.app.app:app", host=config.host, port=config.port, loop="none")


async def sync_clients_and_db():
    session = SessionLocal()
    logger.info("Starting Aircraft_DB and Clients!")

    while True:
        await add_aircrafts_to_db(session)
        await clients(session)
        await asyncio.sleep(config.clients_and_db_update)


async def run():
    logger.info("Starting...")
    global result
    asyncio.get_event_loop().set_debug(False)

    await setup_database()

    if config.debug:
        asyncio.get_event_loop().set_debug(True)
        await asyncio.gather(query_updater.update_query(True), query_updater.update_db())
        await sync_clients_and_db()
        atexit.register(print_result)
        return

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logger.info("Downloading opensky aircraft info database and updating aircraft ")
    await asyncio.gather(query_updater.update_query(True), query_updater.update_db())
    logger.info("Let's start Fastapi")
    asyncio.create_task(asyncio.to_thread(fastapi_start))

    logger.info("Starting all...")

    result = await asyncio.gather(query_updater.update_query(), sync_clients_and_db())


asyncio.run(run())
