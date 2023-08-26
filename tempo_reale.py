import asyncio
import datetime
import logging
import platform

from flask import Flask
from flask.sessions import SessionInterface, SessionMixin
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate, upgrade, init
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.orm import joinedload
from werkzeug.middleware.proxy_fix import ProxyFix

from common_py.common import query_updater
from modules.add_to_db.add_to_db import add_aircrafts_to_db
from modules.blueprint.commonMy.commonMy import commonMy_bp
from modules.blueprint.live.live import live_bp
from modules.blueprint.report.report import report_bp
from modules.blueprint.utility.utility import utility_bp
from modules.blueprint.mappa_personale.mappa_personale import mappa_bp
from modules.clients.clients import clients
from utility.config import SECRET_KEY, FIRST_TIME
from utility.model import db, SessionData



class SQLSession(dict, SessionMixin):
    pass


class SQLSessionInterface(SessionInterface):
    def open_session(self, app, request):
        sid = request.cookies.get(app.config['SESSION_COOKIE_NAME'])
        if not sid:
            sid = URLSafeTimedSerializer(app.secret_key).dumps(dict())
            session = SQLSession()
            session['sid'] = sid
            return session

        session_data = SessionData.query.options(joinedload(SessionData.ricevitore)).filter_by(id=sid).first()
        if session_data:
            session = SQLSession(**session_data.data)
            session['sid'] = session_data.id

            if session_data.ricevitore:
                session['ricevitore'] = session_data.ricevitore

            return session
        request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        session = SQLSession()
        session['sid'] = sid
        return session

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            response.delete_cookie(app.config['SESSION_COOKIE_NAME'], domain=domain)
            return
        if self.get_expiration_time(app, session):
            expiration = self.get_expiration_time(app, session)
        else:
            expiration = datetime.datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']

        sid = session['sid']
        data = dict(session)


        if "uuid" in session:
            ricevitore_uuid = session["uuid"]
            db.session.merge(SessionData(id=sid, data=data, ricevitore_uuid=ricevitore_uuid))
        else:
            db.session.merge(SessionData(id=sid, data=data))
        db.session.commit()

        response.set_cookie(app.config['SESSION_COOKIE_NAME'], sid, expires=expiration, httponly=True, domain=domain)


def create_app():
    app = Flask(__name__)
    app.config["FLASK_APP"] = "tempo_reale.py"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tempo_reale.sqlite'


    app.config['SECRET_KEY'] = SECRET_KEY
    app.config["WTF_CSRF_SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    db.init_app(app)

    app.register_blueprint(live_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(utility_bp)
    app.register_blueprint(commonMy_bp)
    app.register_blueprint(mappa_bp, url_prefix="/mappa")
    app.session_interface = SQLSessionInterface()
    if platform.system() != "Windows":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return app


def setup_database(app):
    with app.app_context():
        db.create_all()
        db.session.commit()
        if FIRST_TIME:
            init()
        #else:
        #    upgrade()


app = create_app()
#Migrate(app, db)
setup_database(app)
bootstrap = Bootstrap(app)


logger = logging.getLogger("MAIN")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
sh = logging.StreamHandler()
logger.addHandler(sh)


def flask_thread():
    app.logger.info("Flask in partenza!")
    if platform.system() != "Windows":
        app.run(host="0.0.0.0", port=83, debug=False)   # DEBUG DEVE RIMANERE SU FALSE, ALTRIMENTI SIGNAL FA CRASHARE
    else:
        app.run(host="localhost", port=830, debug=False) # DEBUG DEVE RIMANERE SU FALSE

logging.basicConfig(level=logging.DEBUG)

def run_in_thread():
    # Esegui il tuo codice qui
    with app.app_context():
        with db.session.no_autoflush:
            # chiamata al database o altre operazioni
            add_aircrafts_to_db()
debug = True
async def run():
    if debug:
        asyncio.get_event_loop().set_debug(True)
        """
        with app.app_context():
            with db.session.no_autoflush:
                await clients()
                return
        """
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.warning("Dipendenze in partenza...")
    with app.app_context():
        await asyncio.gather(query_updater.update_db(), query_updater.update_query(True))
    logger.info("Primi await completati, ora partono gli h24")
    logger.info("Facciamo partire Flask")
    asyncio.create_task(asyncio.to_thread(flask_thread))
    with app.app_context():
        with db.session.no_autoflush:
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(None, run_in_thread)
            logger.info("Si parte ciurma!")
            await asyncio.gather(query_updater.update_query(), clients())




asyncio.run(run())
