import asyncio
import atexit
import logging
import platform
from uuid import uuid4, UUID

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from common_py.common import query_updater
from modules.add_to_db.add_to_db import add_aircrafts_to_db
from modules.blueprint.commonMy.commonMy import commonMy_bp, dologin
from modules.blueprint.live.live import live_bp
from modules.blueprint.my_map.my_map import mappa_bp
from modules.blueprint.report.report import report_bp
from modules.blueprint.utility.utility import utility_bp
from modules.clients.clients import clients
from utility.config import UPDATE, debug, HOST, PORT, DEPLOYEMENT_PORT, DEPLOYEMENT_HOST
from utility.model import engine, Base, SessionLocal, SessionData


def create_app():
    app = FastAPI(title=__name__)
    templates = Jinja2Templates(
        directory="modules/blueprint/utility/templates")

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 500:
            return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
        return HTMLResponse(str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 404:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        return HTMLResponse(str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 400:
            return templates.TemplateResponse("400.html", {"request": request}, status_code=400)
        return HTMLResponse(str(exc.detail), status_code=exc.status_code)

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
    session_db = SessionLocal()
    request.state.session_db = session_db

    logger.debug("Middleware: before roue")

    session_uuid = UUID(str(request.cookies.get("session_uuid", uuid4())))

    if request.url.path not in ["/style.css"]:
        result = await session_db.execute(
            select(SessionData).options(joinedload(SessionData.receiver)).filter_by(session_uuid=session_uuid)
        )
        session: SessionData = result.scalar_one_or_none()

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
    if platform.system() != "Windows":
        uvicorn.run(app, host=DEPLOYEMENT_HOST, port=DEPLOYEMENT_PORT)
    else:
        uvicorn.run(app, host=HOST, port=PORT)


result = ""


def print_result():
    print(result)


atexit.register(print_result)


async def sync_clients_and_db():
    session = SessionLocal()
    logger.info("Starting Aerei_DB!")
    logger.info("Starting Clients!")

    while True:
        await add_aircrafts_to_db(session)
        await clients(session)
        await asyncio.sleep(UPDATE)


async def run():
    global result
    asyncio.get_event_loop().set_debug(False)

    await setup_database()

    if debug:
        asyncio.get_event_loop().set_debug(True)
        await asyncio.gather(query_updater.update_query(True), query_updater.update_db())
        await sync_clients_and_db()
        atexit.register(print_result)
        return

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    await asyncio.gather(query_updater.update_query(True))
    logger.info("Let's start Fastapi")
    asyncio.create_task(asyncio.to_thread(fastapi_start))

    logger.info("Starting all...")

    result = await asyncio.gather(query_updater.update_db(), query_updater.update_query(), sync_clients_and_db())


asyncio.run(run())
