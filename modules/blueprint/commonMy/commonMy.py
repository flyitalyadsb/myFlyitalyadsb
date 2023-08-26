import asyncio
import logging
from functools import wraps

from flask import Blueprint, session, render_template, abort, request, flash, redirect, url_for
from user_agents import parse

from utility.forms import LoginForm
from utility.model import Ricevitore
from common_py.common import query_updater

commonMy_bp = Blueprint('commonMy_bp', __name__, template_folder='templates',
                        static_folder='static')  # static_url_path='assets'
commonMy_bp.logger = logging.getLogger(__name__)

def human_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_agent_string = request.headers.get('User-Agent')
        user_agent = parse(user_agent_string)

        if user_agent.is_bot:
            # Se rilevi un bot, restituisci un messaggio di errore (ad esempio)
            return abort(404)

        # Se non è un bot, continua con la vista originale
        return f(*args, **kwargs)

    return decorated_function


def login_required(f):
    if asyncio.iscoroutinefunction(f):
        @wraps(f)
        async def async_decorated_function(*args, **kwargs):
            if "logged_in" not in session or not session["logged_in"]:
                return redirect(url_for('commonMy_bp.dologin', next_page=request.url))
            return await f(*args, **kwargs)

        return async_decorated_function
    else:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "logged_in" not in session or not session["logged_in"]:
                return redirect(url_for('commonMy_bp.dologin', next_page=request.url))
            return f(*args, **kwargs)

        return decorated_function


@commonMy_bp.route('/login', methods=['POST', 'GET'])
def dologin():
    next_page = request.args.get("next_page")
    if request.method == "GET":
        if next_page:
            session["next"] = next_page
        else:
            session["next"] = request.url_root

    form = LoginForm(request.form)
    if (request.method == 'POST' and form.validate_on_submit()) or (request.method == 'GET' and request.args.get('uuid',
                                                                                                              default=False)):
        uuid = request.args.get('uuid', default=False)
        uuid = uuid.lower() if uuid else form.uuid.data
        check_exist = Ricevitore.query.filter_by(uuid=uuid).first()
        if check_exist:
            session['logged_in'] = True
            session['uuid'] = uuid
        else:
            flash('UUID errata', 'warning')
            return render_template("login.html", form=form)

        #if platform == "Windows":
        #    session['logged_in'] = True
        #    session['uuid'] = "test"

        return redirect(session["next"])
    else:
        return render_template("login.html", form=form)
