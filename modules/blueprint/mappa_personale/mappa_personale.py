import logging
import time

import aiofiles
from utility.model import Ricevitore
from common_py.common import query_updater
from fastapi import APIRouter, Request, HTTPException
from starlette.templating import Jinja2Templates
from fastapi.responses import FileResponse

mappa_bp = APIRouter(prefix="/mappa")
mappa_bp.logger = logging.getLogger(__name__)
path = "modules/blueprint/mappa_personale/templates"
templates = Jinja2Templates(directory="templates")


@mappa_bp.get('/')
def mappa(request: Request):
    return templates.TemplateResponse("index_mappa.html", {"request": request,})


@mappa_bp.get("/data/aircraft.json")
async def aircrafts():
    aircrafts_json = await query_updater.aicrafts_filtered_by_my_receiver(my=True)
    ricevitore: Ricevitore = session["ricevitore"]
    json_aircraft = {"messages": ricevitore.messaggi_al_sec if ricevitore.messaggi_al_sec else 0, "now": time.time(), "aircraft": aircrafts_json}
    return json_aircraft


@mappa_bp.get("/data/receiver.json")
def receiver():
    ricevitore: Ricevitore = session["ricevitore"]
    receiver = {
        "lat": ricevitore.lat,
        "lon": ricevitore.lon,
        "readsb": True,
        "refresh": 1000,
        "version": "flyitalyadsb.com"
    }
    return receiver


@mappa_bp.get("/aircraft_sil/<sil>")
#@cache(max_age=1209600, public=True)
def aircraft_sil(sil):
    return send_file(path + "/aircraft_sil/" + sil)


@mappa_bp.get("/osm_tiles_offline/<osm>")
def osm_tiles_offline(osm):
    return send_file(path + "/osm_tiles_offline/" + osm)


@mappa_bp.get("/libs/<lib>")
#@cache(max_age=7776000, public=True)
#@inflate
def libs(lib):
    try:
        return send_file(path + "/libs/" + lib)
    except:
        mappa_bp.logger.info(f"{lib} non trovato")
        HTTPException(404)

@mappa_bp.get("/style/<style>")
#@cache(max_age=7776000, public=True)
def style(style):
    return send_file(path + style)


@mappa_bp.get("/libs/images/<img>")
def libs_img(img):
    return send_file(path + "/libs/images/" + img)


@mappa_bp.get("/images/<img>")
#@cache(max_age=7776000, public=True)
def images(img):
    return send_file(path + "/images/" + img)


@mappa_bp.get("/flags-tiny/<flag>")
#@cache(max_age=7776000, public=True)
def flags(flag):
    return send_file(path + "/flags-tiny/" + flag)


@mappa_bp.get("/config.js")
async def config():
    async with aiofiles.open(path + "/config.js.jinja2", "r") as f:
        js_template = await f.read()
    ricevitore: Ricevitore = session["ricevitore"]
    rendered_js = render_template_string(js_template, center_lat=ricevitore.lat if ricevitore.lat else ricevitore.lat_avg, center_lon=ricevitore.lon if ricevitore.lon else ricevitore.lon_avg)
    response = make_response(rendered_js)
    response.mimetype = 'application/javascript'
    return response


@mappa_bp.get("/db-<db>/<tag>.js")
def get_database(db, tag):
    return send_file(path + f"/db-{db}/{tag}.js")


@mappa_bp.get("/<script>")
def tar_script(script: str):
    folder = "/images/" if script.endswith(".png") else "/"
    try:
        return send_file(path + folder + script)
    except:
        mappa_bp.logger.info(f"{script} non trovato")
        HTTPException(404)
