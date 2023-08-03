import aiohttp
from flask import Blueprint, render_template, session, redirect, request, jsonify, flash
from utility.forms import MenuForm, SliderForm, OnlyMine
from utility.model import Ricevitore
import platform
import logging
from common_py.commonLiveReport import pagination_func, query_updater
from modules.blueprint.commonMy.commonMy import login_required

live_bp = Blueprint('live_bp', __name__, template_folder='templates',
                    static_folder='static')
live_bp.logger = logging.getLogger(__name__)


@live_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    session["selected_page"] = 1
    session["filter"] = ""
    session["sort"] = "hex"
    form = MenuForm()
    posizione = SliderForm()
    mio = OnlyMine()
    if form.validate_on_submit():
        if form.Mappa.data:
            return redirect("https://mappa.flyitalyadsb.com")
        elif form.Report.data:
            return redirect("/report")  # TODO riuscire a mettere url to funzione report
        elif form.Sito.data:
            return redirect("https://flyitalyadsb.com")
        elif form.Statistiche.data:
            return redirect("https://statistiche.flyitalyadsb.com")
    user: Ricevitore = session["ricevitore"]
    if not user.lon:
        flash("MLAT e FEED non sincronizzati, utilizzo la posizione media degli aerei ricevuti")
        # TODO handle this in the template
    return render_template('index.html', form=form, posizione=posizione, mio=mio)


@live_bp.route("/session/posizione", methods=["POST"])
@login_required
def posizion():
    session["posizione"] = True
    raggio = request.form.get("raggio")
    session["raggio"] = raggio
    ok = {'data': "success"}
    return jsonify(ok)


@live_bp.route("/session/only_mine", methods=["GET", "POST"])
@login_required
def only_mine():
    only_mine_data = request.form.get("only_mine")
    live_bp.logger.debug(only_mine_data)
    if only_mine_data == "solo i miei dati":
        session["only_mine"] = True
    else:
        session["only_mine"] = False
    ok = {'data': "success"}
    return jsonify(ok)



@live_bp.route('/selected_page')
@login_required
def session_data():
    selected_page = {'selected_page': session["selected_page"], "filtered": session["filter"],
                     "sorted": session["sort"]}
    return jsonify(selected_page)


@live_bp.route('/disattiva/<modalita>', methods=["POST"])
@login_required
def disattiva(modalita):
    session[modalita] = False
    ok = {'data': "success"}
    return jsonify(ok)


@live_bp.route("/table")
@login_required
async def table_pagination_func():
    search = request.args.get('search', False).upper()
    sort_by = request.args.get('sort_by', 'hex')
    if sort_by != "hex":
        session["sort"] = sort_by

    new_page = request.args.get("new_page")
    page = request.args.get("page", type=int, default=1)
    if new_page:
        session["selected_page"] = page
    else:
        if page != session["selected_page"]:
            page = session["selected_page"]
    if search and not "search" in session.keys():
        page = 1
        session["search"] = search
    if search and "search" in session.keys() and session["search"]:
        if session["search"] != search:
            page = 1
            session["search"] = search

    user: Ricevitore = session["ricevitore"]

    process_default = True
    if "posizione" in session and session["posizione"]:
        custom_readsb_url = f"http://readsb:30152/?circle={user.lat if user.lat else user.lat_avg},{user.lon if user.lon else user.lon_avg},{session['raggio']}"
        if platform.system() == "Windows":
            custom_readsb_url = f"https://mappa.flyitalyadsb.com/re-api/?circle={user.lat if user.lat else user.lat_avg},{user.lon if user.lon else user.lon_avg},{session['raggio']}"
        async with aiohttp.ClientSession() as session_http:
            data = await query_updater.fetch_data_from_url(live_bp.logger, custom_readsb_url, session_http)
        custom_aircrafts = data["aircraft"]
        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts=custom_aircrafts)
        process_default = False

    elif "only_mine" in session and session["only_mine"]:
        custom_aicrafts = await query_updater.aicrafts_filtered_by_my_receiver()
        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts=custom_aicrafts)
        process_default = False

    if process_default:
        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts=query_updater.aircrafts)
    if search and session["search"]:
        session["filter"] = search
        data_filtered = [row for row in sliced_aircrafts if
                         search in row['hex'] or
                         (row["info"] is not None and row["info"].Registration is not None and search in row[
                             "info"].Registration) or
                         (row.get('flight') is not None and search in row['flight']) or
                         (row.get('squawk') is not None and search in row['squawk']) or
                         (row["info"] is not None and row['info'].Operator is not None and search in row[
                             'info'].Operator)]

        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page, aircrafts=data_filtered,
                                                             live=False)

    if sort_by == "Registrazione":
        sliced_aircrafts.sort(key=lambda x: x["info"].Registration if x["info"] is not None and x[
            "info"].Registration is not None else "")
    elif sort_by == "Operator":
        sliced_aircrafts.sort(
            key=lambda x: x["info"].Operator if x["info"] is not None and x["info"].Operator is not None else "")

    return render_template("table.html", aircrafts=sliced_aircrafts, pagination=pagination)
