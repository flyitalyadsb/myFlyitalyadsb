from flask import render_template, session, send_file, Blueprint
from flask_inflate import inflate
from flask_cachecontrol import cache, dont_cache
from modules.blueprint.commonMy.commonMy import login_required
from common_py.common import query_updater

mappa_bp = Blueprint('mappa_bp', __name__, template_folder='templates',
                     static_folder='static')


@login_required
@mappa_bp.route('/')
def mappa():
    return render_template("index.html")


@login_required
@mappa_bp.route("/chunks/<chunk>")
def chunks(chunk):
    aircrafts = query_updater.aicrafts_filtered_by_my_receiver()

#receivers.json
#chunks.json


@login_required
@mappa_bp.route("/data/<dati>")
@dont_cache()
def data(dati):
    aircrafts = query_updater.aicrafts_filtered_by_my_receiver()


@login_required
@mappa_bp.route("/aircraft_sil/<sil>")
@cache(max_age=1209600, public=True)
def aircraft_sil(sil):
    return send_file("mappa/templates/aircraft_sil/" + sil)


@login_required
@mappa_bp.route("/osm_tiles_offline/<osm>")
def osm_tiles_offline(osm):
    return send_file("mappa/templates/osm_tiles_offline/" + osm)


@login_required
@mappa_bp.route("/libs/<lib>")
@cache(max_age=7776000, public=True)
@inflate
def libs(lib):
    return send_file("mappa/templates/libs/" + lib)


@login_required
@mappa_bp.route("/style/<style>")
@cache(max_age=7776000, public=True)
def style(style):
    return send_file("mappa/templates/" + style)


@login_required
@mappa_bp.route("/libs/images/<img>")
def libs_img(img):
    return send_file("mappa/templates/libs/images/" + img)


@login_required
@mappa_bp.route("/images/<img>")
@cache(max_age=7776000, public=True)
def images(img):
    return send_file("mappa/templates/images/" + img)


@login_required
@mappa_bp.route("/flags-tiny/<flag>")
@cache(max_age=7776000, public=True)
def flags(flag):
    return send_file("mappa/templates/flags-tiny/" + flag)


@login_required
@mappa_bp.route("/config.js")
@dont_cache()
def config():
    return send_file("mappa/templates/config.js")


@login_required
@mappa_bp.route("/db-<db>/<tag>.js")
def get_database(db, tag):
    return send_file(f"mappa/templates/db-{db}/{tag}.js")


@login_required
@mappa_bp.route("/<script>")
def tar_script(script):
    return send_file("mappa/templates/" + script)
