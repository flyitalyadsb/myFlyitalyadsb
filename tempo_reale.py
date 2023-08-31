import asyncio
import logging
import platform
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi_pagination import add_pagination
from common_py.common import query_updater
from modules.add_to_db.add_to_db import add_aircrafts_to_db
from modules.blueprint.commonMy.commonMy import commonMy_bp, dologin
from modules.blueprint.live.live import live_bp
from modules.blueprint.report.report import report_bp
from modules.blueprint.utility.utility import utility_bp
from modules.blueprint.mappa_personale.mappa_personale import mappa_bp
from modules.clients.clients import clients
from utility.config import debug
from utility.model import engine, Base, SessionLocal, SessionData
import uvicorn
from uuid import uuid4, UUID
from fastapi.staticfiles import StaticFiles



def create_app():
    app = FastAPI(title=__name__)
    templates = Jinja2Templates(
        directory="C:\\Users\\Stage_ut\\Desktop\\stage-python\\myFlyitalyadsb\\modules\\blueprint\\utility\\templates")

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
    add_pagination(app)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    if platform.system() != "Windows":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return app


async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app = create_app()

logger = logging.getLogger("MAIN")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@app.middleware("http")
async def middleware(request: Request, call_next):
    session_db = SessionLocal()
    request.state.session_db = session_db

    logger.debug("Middleware: prima della route")
    session_uuid = request.cookies.get("session_uuid")
    if not session_uuid:
        uuid = uuid4()
        session = SessionData(session_uuid=uuid)
        request.state.session = session
        response = await dologin(request, next_page=str(request.url))
        response.set_cookie(key="session_uuid", value=uuid, httponly=True)
        session_db.add(session)
        await session_db.commit()
        await session_db.close()
        return response

    else:
        session_uuid = UUID(str(session_uuid))
        logger.debug(f"Session id trovata! {session_uuid}")
        if request.url.path not in ["/style.css"]:
            result = await session_db.execute(
                select(SessionData).options(joinedload(SessionData.ricevitore)).filter_by(session_uuid=session_uuid))
            session: SessionData = result.scalar_one_or_none()
            logger.debug(f"Selected page before response: {session.selected_page}, url path: {request.url.path}")
            request.state.session = session
            if session.logged_in:
                response = await call_next(request)  # Questo passa il controllo alla route
            else:
                response = await dologin(request, next_page=str(request.url))
            await session_db.commit()
            logger.debug(f"Selected page after response: {session.selected_page}, url path: {request.url.path}")
            await session_db.close()
            return response
        else:
            response = await call_next(request)
            return response



def fastapi_start():
    app.logger = logging.getLogger("Fastapi")
    app.logger.info("Fastapi in partenza!")
    if platform.system() != "Windows":
        uvicorn.run(app, host="0.0.0.0", port=83)
    else:
        uvicorn.run(app, host="localhost", port=830)


async def run():
    await setup_database()
    if debug:
        await clients()
        return

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.warning("Dipendenze in partenza...")
    asyncio.get_event_loop().set_debug(False)

    await asyncio.gather(query_updater.update_db(), query_updater.update_query(True))
    logger.info("Primi await completati, ora partono gli h24")
    logger.info("Facciamo partire Flask")
    asyncio.create_task(asyncio.to_thread(fastapi_start))
    logger.info("Si parte ciurma!")
    await query_updater.update_query()
    await asyncio.gather(clients())


asyncio.run(run())
