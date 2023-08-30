import asyncio
import logging
import platform
from fastapi import FastAPI, Request
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from common_py.common import query_updater
from modules.add_to_db.add_to_db import add_aircrafts_to_db
from modules.blueprint.commonMy.commonMy import commonMy_bp, dologin
from modules.blueprint.live.live import live_bp
from modules.blueprint.report.report import report_bp
# from modules.blueprint.utility.utility import utility_bp
from modules.blueprint.mappa_personale.mappa_personale import mappa_bp
from modules.clients.clients import clients
from utility.config import debug
from utility.model import engine, Base, SessionLocal, SessionData, Ricevitore
import uvicorn
from uuid import uuid4, UUID



def create_app():
    app = FastAPI(title=__name__)
    app.include_router(live_bp)
    app.include_router(report_bp)
    # app.include_router(utility_bp)
    app.include_router(commonMy_bp)
    app.include_router(mappa_bp)

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
async def my_middleware(request: Request, call_next):
    session_db = SessionLocal()
    request.state.session_db = session_db

    logger.debug("Middleware: prima della route")
    session_uuid = request.cookies.get("session_uuid")
    if not session_uuid:
        if request.url.path not in ["/login"]:
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
        print(f"Session id trovata! {session_uuid}")
        result = await session_db.execute(select(SessionData).options(joinedload(SessionData.ricevitore)).filter_by(session_uuid=session_uuid))
        session: SessionData = result.scalar_one_or_none()
        request.state.session = session
        if session.logged_in:
            response = await call_next(request)  # Questo passa il controllo alla route
        else:
            response = await dologin(request, next_page=str(request.url))
            await session_db.commit()
        await session_db.close()
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
        asyncio.get_event_loop().set_debug(True)
        await asyncio.gather(query_updater.update_db(), query_updater.update_query(True))
        await clients()
        return

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.warning("Dipendenze in partenza...")
    logger.info("Primi await completati, ora partono gli h24")
    logger.info("Facciamo partire Flask")
    asyncio.create_task(asyncio.to_thread(fastapi_start))
    logger.info("Si parte ciurma!")
    await asyncio.gather(add_aircrafts_to_db(), query_updater.update_query(), clients())


asyncio.run(run())
