import logging

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from starlette.responses import RedirectResponse

from utility.forms import LoginForm
from utility.model import Ricevitore
from common_py.common import flash, get_flashed_message

commonMy_bp = APIRouter()
templates = Jinja2Templates(
    directory="modules/blueprint/commonMy/templates")
commonMy_bp.logger = logging.getLogger(__name__)
templates.env.globals["get_flashed_messages"] = get_flashed_message


@commonMy_bp.get('/login')
@commonMy_bp.post('/login')
async def dologin(request: Request, next_page: str = None, uuid: str = None):
    session_db = request.state.session_db
    if next_page:
        request.state.session.next = next_page
    else:
        request.state.session.next = str(request.url).rstrip(request.url.path)

    form = await LoginForm.from_formdata(request)
    if (request.method == 'POST' and await form.validate_on_submit()) or (Request.method == 'GET' and uuid):
        uuid = uuid.lower() if uuid else form.uuid.data
        check_exist = await session_db.execute(select(Ricevitore).filter_by(uuid=uuid))
        check_exist = check_exist.scalar_one_or_none()
        if check_exist:
            request.state.session.logged_in = True
            request.state.session.uuid = uuid
            request.state.ricevitore = check_exist
        else:
            flash(request, 'UUID errata')
            return templates.TemplateResponse("login.html", {"request": request, "form": form})

        return RedirectResponse(url=request.state.session.next)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "form": form})
