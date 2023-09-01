import logging
import time
import os

from utility.model import Ricevitore
from common_py.common import query_updater
from fastapi import APIRouter, Request, HTTPException
from starlette.templating import Jinja2Templates
from fastapi.responses import FileResponse

mappa_bp = APIRouter(prefix="/mappa")
mappa_bp.logger = logging.getLogger(__name__)
path = "modules/blueprint/mappa_personale/templates"
templates = Jinja2Templates(directory=path)


@mappa_bp.get('/')
async def mappa(request: Request):
    return templates.TemplateResponse("index_mappa.html", {"request": request, })


@mappa_bp.get("/data/aircraft.json")
async def aircrafts(request: Request):
    session = request.state.session
    aircrafts_json = await query_updater.aicrafts_filtered_by_my_receiver(session, my=True)
    ricevitore: Ricevitore = session.ricevitore
    json_aircraft = {"messages": ricevitore.messaggi_al_sec if ricevitore.messaggi_al_sec else 0, "now": time.time(),
                     "aircraft": aircrafts_json}
    return json_aircraft


@mappa_bp.get("/data/receiver.json")
async def receiver(request: Request):
    session = request.state.session
    ricevitore: Ricevitore = session.ricevitore
    receiver = {
        "lat": ricevitore.lat,
        "lon": ricevitore.lon,
        "readsb": True,
        "refresh": 1000,
        "version": "flyitalyadsb.com"
    }
    return receiver


@mappa_bp.get("/aircraft_sil/{sil}", response_class=FileResponse)
async def aircraft_sil(sil: str):
    response = FileResponse(os.path.join(path + "/aircraft_sil/" + sil), media_type="image/x-icon")
    response.headers["Cache-Control"] = "public, max-age=1209600"
    return response


@mappa_bp.get("/osm_tiles_offline/{osm}")
async def osm_tiles_offline(osm: str):
    return FileResponse(os.path.join(path + "/osm_tiles_offline/" + osm), media_type="image/x-icon")


@mappa_bp.get("/libs/{lib}", response_class=FileResponse)
# @inflate
async def libs(lib: str):
    render_path = os.path.join(path + "/libs/" + lib)
    if os.path.exists(render_path):
        if render_path.endswith(".js"):
            response = FileResponse(os.path.join(path + "/libs/" + lib), media_type="application/javascript")
        elif render_path.endswith("css"):
            response = FileResponse(os.path.join(path + "/libs/" + lib), media_type="text/css")
        else:
            response = FileResponse(os.path.join(path + "/libs/" + lib))
        response.headers["Cache-Control"] = "public, max-age=7776000"
        return response
    else:
        mappa_bp.logger.info(f"{lib} non trovato")
        raise HTTPException(404)


@mappa_bp.get("/style/{style}")
async def style(style: str):
    response = FileResponse(os.path.join(path + style), )
    response.headers["Cache-Control"] = "public, max-age=7776000"

    return response


@mappa_bp.get("/libs/images/{img}")
async def libs_img(img: str):
    render_path = os.path.join(path + "/libs/images/" + img)
    if os.path.exists(render_path):
        response = FileResponse(render_path, media_type="image/x-icon")
        return response
    else:
        mappa_bp.logger.info(f"{img} non trovato")
        raise HTTPException(404)


@mappa_bp.get("/images/{img}")
async def images(img: str):
    render_path = os.path.join(path + "/images/" + img)
    if os.path.exists(render_path):
        response = FileResponse(render_path, media_type="image/x-icon")
        response.headers["Cache-Control"] = "public, max-age=7776000"
        return response
    else:
        mappa_bp.logger.info(f"{img} non trovato")
        raise HTTPException(404)


@mappa_bp.get("/flags-tiny/{flag}")
async def flags(flag: str):
    response = FileResponse(os.path.join(path + "/flags-tiny/" + flag), media_type="image/x-icon")
    response.headers["Cache-Control"] = "public, max-age=7776000"
    return response


@mappa_bp.get("/config.js")
async def config(request: Request):
    ricevitore: Ricevitore = request.state.session.ricevitore
    rendered_js = templates.TemplateResponse(os.path.join(path, "/config.js.jinja2"), {
        "request": request,
        "center_lat": ricevitore.lat if ricevitore.lat else ricevitore.lat_avg,
        "center_lon": ricevitore.lon if ricevitore.lon else ricevitore.lon_avg
    }, media_type="application/javascript")
    return rendered_js


@mappa_bp.get("/db-{db}/{tag}.js")
async def get_database(db: str, tag: str):
    response = FileResponse(os.path.join(path + f"/db-{db}/{tag}.js"), media_type="application/json")
    response.headers["Cache-Control"] = "public, max-age=7776000"
    response.headers["Content-Encoding"] = "gzip"

    return response


@mappa_bp.get("/{script}")
async def general_script(script: str):
    folder = "/images/" if script.endswith(".png") else "/"
    render_path = os.path.join(path + folder + script)
    if os.path.exists(render_path):
        if folder == "/images/":
            response = FileResponse(render_path, media_type="image/x-icon")
        else:
            response = FileResponse(render_path, media_type="application/javascript")
        return response
    else:
        mappa_bp.logger.info(f"{script} non trovato")
        raise HTTPException(404)
