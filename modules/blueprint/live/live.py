import aiohttp
from utility.forms import MenuForm, SliderForm, OnlyMine
from utility.model import Ricevitore, SessionLocal
import platform
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from common_py.commonLiveReport import pagination_func, query_updater
import aiofiles
from fastapi import APIRouter, Request, Form, Depends, Response
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
from utility.model import SessionDataPydantic


live_bp = APIRouter()
templates = Jinja2Templates(directory="C:\\Users\\Stage_ut\\Desktop\\stage-python\\myFlyitalyadsb\\modules\\blueprint\\live\\templates")

live_bp.logger = logging.getLogger(__name__)

session_db: AsyncSession = SessionLocal()


@live_bp.get("/", tags=["users"])
@live_bp.post("/", tags=["users"])
async def index(request: Request):
    session: SessionDataPydantic = request.state.session
    session.selected_page = 1
    session.filter = ""
    session.sort = "hex"
    form = await MenuForm.from_formdata(request)
    posizione = await SliderForm.from_formdata(request)
    mio = await OnlyMine.from_formdata(request)
    if await form.validate_on_submit():
        if await form.Mappa_my.data:
            return RedirectResponse("/mappa")  # TODO riuscire a mettere url to funzione mappa
        elif await form.Mappa.data:
            return RedirectResponse("https://mappa.flyitalyadsb.com")
        elif await form.Report.data:
            return RedirectResponse("/report")  # TODO riuscire a mettere url to funzione report
        elif await form.Sito.data:
            return RedirectResponse("https://flyitalyadsb.com")
        elif await form.Grafici.data:
            return RedirectResponse("https://statistiche.flyitalyadsb.com")
    ricevitore: Ricevitore = session.ricevitore
    if ricevitore and not ricevitore.lon:
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
async def stazioni(request: Request):
    ricevitore: Ricevitore = session.ricevitore
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
def posizion(request: Request):
    session.posizione = True
    raggio = Request.get("raggio")
    session.raggio = raggio
    ok = {'data': "success"}
    return ok


@live_bp.get("/session/only_mine")
@live_bp.post("/session/only_mine")
async def only_mine(request: Request, only_mine_data: Annotated[str, Form()]):
    live_bp.logger.debug(only_mine_data)
    if only_mine_data == "solo i miei dati":
        session.only_mine = True
    else:
        session.only_mine = False
    ok = {'data': "success"}
    return ok


@live_bp.get('/selected_page')
def session_data(request: Request):
    selected_page = {'selected_page': session.selected_page, "filtered": session.filter,
                     "sorted": session.sort}
    return selected_page


@live_bp.post('/disattiva/<modalita>')
def disattiva(request: Request,modalita):
    session.modalita = False
    ok = {'data': "success"}
    return ok


@live_bp.get("/table")
async def table_pagination_func(request:Request, search: str = None, sort_by: str = "hex", new_page: str = None, page: int = 1):
    if search:
        search = search.upper()
    if sort_by != "hex":
        session.sort = sort_by

    if new_page:
        session.selected_page = page
    else:
        if page != session.selected_page:
            page = session.selected_page
    if search and not session.search:
        page = 1
        session.search = search
    if search and session.search:
        if session.search != search:
            page = 1
            session.search = search

    user: Ricevitore = session.ricevitore

    process_default = True
    if session.posizione:
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
