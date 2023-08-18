import logging
import time

import aiofiles
from flask import render_template, send_file, Blueprint, jsonify, session, abort, render_template_string, make_response
from utility.model import Ricevitore
from flask_inflate import inflate
from flask_cachecontrol import cache, dont_cache
from modules.blueprint.commonMy.commonMy import login_required
from common_py.common import query_updater

mappa_bp = Blueprint('mappa_bp', __name__, template_folder='templates',
                     static_folder='static')
mappa_bp.logger = logging.getLogger(__name__)
path = "modules/blueprint/mappa_personale/templates"


@login_required
@mappa_bp.route('/')
def mappa():
    return render_template("index_mappa.html")


"""
@login_required
@mappa_bp.route("/chunks/<chunk>")
async def chunks():
    aircrafts = await query_updater.aicrafts_filtered_by_my_receiver()
    return aircrafts
"""

@login_required
@mappa_bp.route("/data/aircraft.json")
async def aircrafts():
    aircrafts_json = await query_updater.aicrafts_filtered_by_my_receiver(my=True)
    json_aircraft = {"messages": 0, "now": time.time(), "aircraft": aircrafts_json}
    return jsonify(json_aircraft)


@login_required
@mappa_bp.route("/data/receiver.json")
@dont_cache()
def receiver():
    ricevitore: Ricevitore = session["ricevitore"]
    receiver = {
        "lat": ricevitore.lat,
        "lon": ricevitore.lon,
        "readsb": True,
        "refresh": 1000,
        "version": "flyitalyadsb.com"
    }
    return jsonify(receiver)


@login_required
@mappa_bp.route("/aircraft_sil/<sil>")
@cache(max_age=1209600, public=True)
def aircraft_sil(sil):
    return send_file(path + "/aircraft_sil/" + sil)


@login_required
@mappa_bp.route("/osm_tiles_offline/<osm>")
def osm_tiles_offline(osm):
    return send_file(path + "/osm_tiles_offline/" + osm)


@login_required
@mappa_bp.route("/libs/<lib>")
@cache(max_age=7776000, public=True)
@inflate
def libs(lib):
    return send_file(path + "/libs/" + lib)


@login_required
@mappa_bp.route("/style/<style>")
@cache(max_age=7776000, public=True)
def style(style):
    return send_file(path + style)


@login_required
@mappa_bp.route("/libs/images/<img>")
def libs_img(img):
    return send_file(path + "/libs/images/" + img)


@login_required
@mappa_bp.route("/images/<img>")
@cache(max_age=7776000, public=True)
def images(img):
    return send_file(path + "/images/" + img)


@login_required
@mappa_bp.route("/flags-tiny/<flag>")
@cache(max_age=7776000, public=True)
def flags(flag):
    return send_file(path + "/flags-tiny/" + flag)


@login_required
@mappa_bp.route("/config.js")
async def config():
    async with aiofiles.open(path + "/config.js.jinja2", "r") as f:
        js_template = await f.read()
    ricevitore: Ricevitore = session["ricevitore"]
    rendered_js = render_template_string(js_template, center_lat=ricevitore.lat if ricevitore.lat else ricevitore.lat_avg, center_lon=ricevitore.lon if ricevitore.lon else ricevitore.lon_avg)
    response = make_response(rendered_js)
    response.mimetype = 'application/javascript'
    return response


@login_required
@mappa_bp.route("/db-<db>/<tag>.js")
def get_database(db, tag):
    return send_file(path + f"/db-{db}/{tag}.js")


@login_required
@mappa_bp.route("/<script>")
def tar_script(script: str):
    folder = "/images/" if script.endswith(".png") else "/"
    try:
        return send_file(path + folder + script)
    except:
        mappa_bp.logger.info(f"{script} non trovato")
        abort(404)
