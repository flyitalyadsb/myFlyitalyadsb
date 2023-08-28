import asyncio
import logging
from functools import wraps
from fastapi import APIRouter, Request
from utility.forms import LoginForm
from utility.model import Ricevitore, SessionLocal
from sqlalchemy import select
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates


session_db = SessionLocal()
commonMy_bp = APIRouter()
templates = Jinja2Templates(directory="./templates")
commonMy_bp.logger = logging.getLogger(__name__)




def login_required(f):
    if asyncio.iscoroutinefunction(f):
        @wraps(f)
        async def async_decorated_function(request: Request, *args, **kwargs):
            if request.session_data.logged_in:
                login_url = commonMy_bp.url_path_for("dologin")
                return RedirectResponse(url=f"{login_url}?next_page={Request.url}")
            return await f(*args, **kwargs)

        return async_decorated_function
    else:
        @wraps(f)
        def decorated_function(request: Request, *args, **kwargs):
            if request.session_data.logged_in:
                login_url = commonMy_bp.url_path_for("dologin")
                return RedirectResponse(url=f"{login_url}?next_page={Request.url}")
            return f(*args, **kwargs)

        return decorated_function


@commonMy_bp.get('/login')
@commonMy_bp.post('/login')
async def dologin(next_page: int=None, uuid: str = None):
    if Request.method == "GET":
        if next_page:
            session["next"] = next_page
        else:
            session["next"] = Request.url_root

    form = LoginForm(Request.form)
    if (Request.method == 'POST' and form.validate_on_submit()) or (Request.method == 'GET' and uuid):
        uuid = uuid.lower() if uuid else form.uuid.data
        check_exist = await session_db.execute(select(Ricevitore).filter_by(uuid=uuid))
        check_exist = check_exist.scalar_one_or_none()
        if check_exist:
            session['logged_in'] = True
            session['uuid'] = uuid
        else:
            flash('UUID errata', 'warning')
            return templates.TemplateResponse("login.html", {"form":form})

        #if platform == "Windows":
        #    session['logged_in'] = True
        #    session['uuid'] = "test"

        return RedirectResponse(url=session["next"])
    else:
        return templates.TemplateResponse("login.html", {"form": form})
