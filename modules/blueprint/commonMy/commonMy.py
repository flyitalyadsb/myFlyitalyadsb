import logging

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from common_py.common import flash, get_flashed_message
from utility.forms import LoginForm
from utility.model import Receiver, SessionData

commonMy_bp = APIRouter()
templates = Jinja2Templates(
    directory="modules/blueprint/commonMy/templates")
commonMy_bp.logger = logging.getLogger(__name__)
templates.env.globals["get_flashed_messages"] = get_flashed_message


async def search_receiver_by_ip(session_db: AsyncSession, ip: str) -> Receiver:
    result: Result = await session_db.execute(select(Receiver).filter_by(ip=ip))
    return result.scalar_one_or_none()


def real_login(request: Request, uuid: str, check_exist: Receiver):
    request.state.session.logged_in = True
    request.state.session.uuid = uuid
    request.state.ricevitore = check_exist


async def check_ip(request: Request, session_db: AsyncSession) -> Receiver:
    forwarded_ip = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_ip.split(",")[0] if forwarded_ip else request.client.host
    receiver = await search_receiver_by_ip(session_db, client_ip)
    return receiver


@commonMy_bp.api_route('/login', methods=["GET", "POST"])
async def dologin(request: Request, next_page: str = None, uuid: str = None):
    session_db: AsyncSession = request.state.session_db
    session: SessionData = request.state.session
    if next_page:
        request.state.session.next = next_page
    else:
        request.state.session.next = str(request.url).rstrip(request.url.path)

    receiver = await check_ip(request, session_db)
    if receiver:
        real_login(request, receiver.uuid, receiver)
        return RedirectResponse(url=request.state.session.next)

    form = await LoginForm.from_formdata(request)
    if (request.method == 'POST' and await form.validate_on_submit()) or (Request.method == 'GET' and uuid):
        session.logging = False
        uuid = uuid.lower() if uuid else form.uuid.data
        check_exist = await session_db.execute(select(Receiver).filter_by(uuid=uuid))
        check_exist = check_exist.scalar_one_or_none()
        if check_exist:
            real_login(request, uuid, check_exist)
        else:
            flash(request, 'UUID errata')
            return templates.TemplateResponse("login.html", {"request": request, "form": form})

        return RedirectResponse(url=request.state.session.next, status_code=302)
    else:
        session.logging = True
        return templates.TemplateResponse("login.html", {"request": request, "form": form})
