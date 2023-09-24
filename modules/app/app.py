import asyncio
import logging
import platform

from starlette.responses import Response
from uuid import uuid4, UUID
from fastapi import FastAPI, Request
from modules.blueprint.commonMy.commonMy import commonMy_bp, dologin
from modules.blueprint.am_i_feeding.am_i_feeding import amIFeeding_bp
from modules.blueprint.live.live import live_bp
from modules.blueprint.my_map.my_map import mappa_bp
from modules.blueprint.report.report import report_bp
from modules.blueprint.utility.utility import utility_bp
from fastapi.staticfiles import StaticFiles

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from utility.model import SessionLocal, SessionData


def create_app():
    app = FastAPI(title=__name__)
    app.include_router(live_bp)
    app.include_router(report_bp)
    app.include_router(utility_bp)
    app.include_router(commonMy_bp)
    app.include_router(mappa_bp)
    app.include_router(amIFeeding_bp)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    if platform.system() != "Windows":
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return app


app = create_app()
logger = logging.getLogger("MAIN")


@app.middleware("http")
async def middleware(request: Request, call_next):
    if request.method not in ["POST", "GET"]:
        return Response("Method not allowed", status_code=405)

    session_db = SessionLocal()
    request.state.session_db = session_db

    logger.debug("Middleware: before route")

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
        if session.logging and request.url.path == "/login":
            response = await call_next(request)
        else:
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
