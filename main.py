import asyncio
import atexit
import logging
import platform
from uuid import uuid4, UUID

import uvicorn
from fastapi import FastAPI, Request
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from common_py.common import query_updater, print_result
from modules.add_to_db.add_to_db import add_aircrafts_to_db
from modules.blueprint.commonMy.commonMy import commonMy_bp, dologin
from modules.blueprint.live.live import live_bp
from modules.blueprint.my_map.my_map import mappa_bp
from modules.blueprint.report.report import report_bp
from modules.blueprint.utility.utility import utility_bp
from modules.clients.clients import clients
from utility.config import config
from utility.model import engine, Base, SessionLocal, SessionData


def create_app():
    app = FastAPI(title=__name__)
    app.include_router(live_bp)
    app.include_router(report_bp)
    app.include_router(utility_bp)
    app.include_router(commonMy_bp)
    app.include_router(mappa_bp)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    if platform.system() != "Windows":
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return app


async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app = create_app()
logger = logging.getLogger("MAIN")


@app.middleware("http")
async def middleware(request: Request, call_next):
    if request.method not in ["POST", "GET"]:
        return Response("Method not allowed", status_code=405)
    session_db = SessionLocal()
    request.state.session_db = session_db

    logger.debug("Middleware: before roue")

    session_uuid = UUID(str(request.cookies.get("session_uuid", uuid4())))

    if request.url.path not in ["/style.css"]:
        result_middleware = await session_db.execute(
            select(SessionData).options(joinedload(SessionData.receiver)).filter_by(session_uuid=session_uuid)
        )
        session: SessionData = result_middleware.scalar_one_or_none()

        if not session:
            session = SessionData(session_uuid=session_uuid)
            session_db.add(session)

        request.state.session = session

        if not session.logged_in:
            response = await dologin(request, next_page=str(request.url))
            response.set_cookie(key="session_uuid", value=session_uuid, httponly=True)
        else:
            response = await call_next(request)

        await session_db.commit()
        logger.debug(f"Selected page after response: {session.selected_page}, url path: {request.url.path}")
    else:
        response = await call_next(request)

    await session_db.close()
    return response


def fastapi_start():
    app.logger = logging.getLogger("Fastapi")
    app.logger.info("Starting Fastapi!")
    uvicorn.run(app, host=config.host, port=config.port)


result = ""
atexit.register(print_result, result)


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
    asyncio.get_event_loop().set_debug(True)

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
