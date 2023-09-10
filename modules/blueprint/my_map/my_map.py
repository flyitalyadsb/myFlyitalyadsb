import logging
import os
import time

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from starlette.templating import Jinja2Templates

from common_py.common import query_updater
from utility.model import Receiver

mappa_bp = APIRouter(prefix="/map")
mappa_bp.logger = logging.getLogger(__name__)
path = "modules/blueprint/mappa_personale/templates"
templates = Jinja2Templates(directory=path)


@mappa_bp.get('/')
async def map_tar1090(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "MyFlyitalyadsb"})


@mappa_bp.get("/data/aircraft.json")
async def aircraft(request: Request):
    session = request.state.session
    aircrafts_json = await query_updater.aicrafts_filtered_by_my_receiver(session, my=True)
    ricevitore: Receiver = session.receiver
    json_aircraft = {"messages": ricevitore.messagges_per_sec if not ricevitore.messagges_per_sec is None else 0,
                     "now": time.time(),
                     "aircraft": aircrafts_json}
    return json_aircraft


@mappa_bp.get("/data/receiver.json")
async def receiver(request: Request):
    session = request.state.session
    ricevitore: Receiver = session.receiver
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


@mappa_bp.get("/libs/{lib}", response_class=FileResponse)  # todo inflate
async def libs(lib: str):
    render_path = os.path.join(path + "/libs/" + lib)
    if os.path.exists(render_path):
        if render_path.endswith(".js"):
            response = FileResponse(os.path.join(path + "/libs/" + lib), media_type="application/javascript")
        elif render_path.endswith(".css"):
            response = FileResponse(os.path.join(path + "/libs/" + lib), media_type="text/css")
        else:
            response = FileResponse(os.path.join(path + "/libs/" + lib))
        response.headers["Cache-Control"] = "public, max-age=7776000"
        return response
    else:
        mappa_bp.logger.info(f"{lib} not found")
        raise HTTPException(404)


@mappa_bp.get("/style/{style}")
async def style(style: str):
    response = FileResponse(os.path.join(path + style), media_type="text/css")
    response.headers["Cache-Control"] = "public, max-age=7776000"

    return response


@mappa_bp.get("/libs/images/{img}")
async def libs_img(img: str):
    render_path = os.path.join(path + "/libs/images/" + img)
    if os.path.exists(render_path):
        response = FileResponse(render_path, media_type="image/x-icon")
        return response
    else:
        mappa_bp.logger.info(f"{img} not found")
        raise HTTPException(404)


@mappa_bp.get("/images/{img}")
async def images(img: str):
    render_path = os.path.join(path + "/images/" + img)
    if os.path.exists(render_path):
        response = FileResponse(render_path, media_type="image/x-icon")
        response.headers["Cache-Control"] = "public, max-age=7776000"
        return response
    else:
        mappa_bp.logger.info(f"{img} not found")
        raise HTTPException(404)


@mappa_bp.get("/flags-tiny/{flag}")
async def flags(flag: str):
    response = FileResponse(os.path.join(path + "/flags-tiny/" + flag), media_type="image/x-icon")
    response.headers["Cache-Control"] = "public, max-age=7776000"
    return response


@mappa_bp.get("/config.js")
async def config(request: Request):
    ricevitore: Receiver = request.state.session.receiver
    rendered_js = templates.TemplateResponse(os.path.join(path, "/config.js.jinja2"), {
        "request": request,
        "center_lat": ricevitore.lat if ricevitore.lat else ricevitore.lat_avg,
        "center_lon": ricevitore.lon if ricevitore.lon else ricevitore.lon_avg
    }, media_type="application/javascript")
    return rendered_js


@mappa_bp.get("/db2/{tag}.js")
async def get_database(tag: str):
    response = FileResponse(os.path.join(path + f"/db2/{tag}.js"))
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Connection"] = "keep-alive"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Encoding"] = "gzip"

    return response


@mappa_bp.get("/{script}")
async def general_script(script: str):
    folder = "/images/" if script.endswith(".png") else "/"
    render_path = os.path.join(path + folder + script)
    if os.path.exists(render_path):
        if folder == "/images/":
            response = FileResponse(render_path, media_type="image/x-icon")
        elif render_path.endswith(".css"):
            response = FileResponse(render_path, media_type="text/css")
        else:
            response = FileResponse(render_path, media_type="application/javascript")
        return response
    else:
        mappa_bp.logger.info(f"{script} not found")
        raise HTTPException(404)
