import aiohttp
from utility.forms import MenuForm, SliderForm, OnlyMine
from utility.model import Ricevitore, SessionLocal
import platform
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from common_py.commonLiveReport import pagination_func, query_updater
from modules.blueprint.commonMy.commonMy import login_required
import aiofiles
from fastapi import APIRouter, Request, Form, Depends, Response
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

live_bp = APIRouter()
templates = Jinja2Templates(directory="./templates")

live_bp.logger = logging.getLogger(__name__)

session_db: AsyncSession = SessionLocal()


@live_bp.get("/", tags=["users"])
@live_bp.post("/", tags=["users"])
@login_required
def index(request: Request):
    request.session_data.selected_page = 1
    request.session_data.filter = ""
    request.session_data.sort = "hex"
    form = MenuForm()
    posizione = SliderForm()
    mio = OnlyMine()
    if form.validate_on_submit():
        if form.Mappa_my.data:
            return RedirectResponse("/mappa")  # TODO riuscire a mettere url to funzione mappa
        elif form.Mappa.data:
            return RedirectResponse("https://mappa.flyitalyadsb.com")
        elif form.Report.data:
            return RedirectResponse("/report")  # TODO riuscire a mettere url to funzione report
        elif form.Sito.data:
            return RedirectResponse("https://flyitalyadsb.com")
        elif form.Grafici.data:
            return RedirectResponse("https://statistiche.flyitalyadsb.com")
    ricevitore: Ricevitore = request.session_data.ricevitore
    if not ricevitore.lon:
        flash("MLAT e FEED non sincronizzati, utilizzo la posizione media degli aerei ricevuti")
        # TODO handle this in the template
    return templates.TemplateResponse('index.html',
                                      {"request": request, "form": form, "posizione": posizione, "mio": mio, "ricevitore": ricevitore})


path = "modules/blueprint/live/templates"


async def get_peer_info(uuid):
    query = await session_db.execute(select(Ricevitore).filter_by(uuid=uuid))
    ric: Ricevitore = query.scalar_one_or_none()
    return \
        {
            'lat': ric.lat if ric.lat else ric.lat_avg,
            'lon': ric.lon if ric.lon else ric.lon_avg,
            'nome': ric.name if ric.name else ric.uuid
        }


@live_bp.get("/config.js")
@login_required
async def stazioni(request: Request, ricevitore: Ricevitore = Depends(get_session_data)):
    async with aiofiles.open("path/config.js.jinja2", mode="r") as f:
        js_template = await f.read()

    stazione_centrale_data = await get_peer_info(ricevitore.uuid)
    stazioni_collegate_data = await asyncio.gather(
        *(get_peer_info(ricevitore.uuid) for ricevitore in ricevitore.peers)
    )

    rendered_js = templates.TemplateResponse(
        "config.js.jinja2",
        {
            "request": request,
            "stazioneCentrale": stazione_centrale_data,
            "stazioniCollegate": stazioni_collegate_data
        }
    ).body.decode()

    return Response(content=rendered_js, media_type="application/javascript")

@live_bp.post("/session/posizione")
@login_required
def posizion(request: Request):
    request.session_data.posizione = True
    raggio = Request.get("raggio")
    request.session_data.raggio = raggio
    ok = {'data': "success"}
    return ok


@live_bp.get("/session/only_mine")
@live_bp.post("/session/only_mine")
@login_required
async def only_mine(request: Request, only_mine_data: Annotated[str, Form()]):
    live_bp.logger.debug(only_mine_data)
    if only_mine_data == "solo i miei dati":
        request.session_data.only_mine = True
    else:
        request.session_data.only_mine = False
    ok = {'data': "success"}
    return ok


@live_bp.get('/selected_page')
@login_required
def session_data(request: Request):
    selected_page = {'selected_page': request.session_data.selected_page, "filtered": request.session_data.filter,
                     "sorted": request.session_data.sort}
    return selected_page


@live_bp.post('/disattiva/<modalita>')
@login_required
def disattiva(request: Request,modalita):
    request.session_data.modalita = False
    ok = {'data': "success"}
    return ok


@live_bp.get("/table")
@login_required
async def table_pagination_func(request:Request, search: str = None, sort_by: str = "hex", new_page: str = None, page: int = 1):
    if search:
        search = search.upper()
    if sort_by != "hex":
        request.session_data.sort = sort_by

    if new_page:
        request.session_data.selected_page = page
    else:
        if page != request.session_data.selected_page:
            page = request.session_data.selected_page
    if search and not request.session_data.search:
        page = 1
        request.session_data.search = search
    if search and request.session_data.search:
        if request.session_data.search != search:
            page = 1
            request.session_data.search = search

    user: Ricevitore = request.session_data.ricevitore

    process_default = True
    if request.session_data.posizione:
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

    return templates.TemplateResponse("table.html",
                                      {"request": request, "aircrafts": sliced_aircrafts, "pagination": pagination})

@live_bp.get("/data_raw")
def all_aircrafts_raw():
    return query_updater.aircrafts_raw
