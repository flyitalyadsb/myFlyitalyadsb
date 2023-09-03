import asyncio
import logging
import platform
import random

import aiohttp
from fastapi import APIRouter, Request, Response, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.responses import RedirectResponse

from common_py.commonLiveReport import pagination_func, query_updater
from utility.forms import MenuForm, SliderForm, OnlyMine
from utility.model import Ricevitore
from utility.model import SessionData

live_bp = APIRouter()
templates = Jinja2Templates(
    directory="modules/blueprint/live/templates")

live_bp.logger = logging.getLogger(__name__)


@live_bp.get("/", tags=["users"])
@live_bp.post("/", tags=["users"])
async def index(request: Request):
    session: SessionData = request.state.session
    form = await MenuForm.from_formdata(request)
    posizione = await SliderForm.from_formdata(request)
    mio = await OnlyMine.from_formdata(request)
    if await form.validate_on_submit():
        if form.Mappa_my.data:
            return RedirectResponse("/mappa", status_code=status.HTTP_303_SEE_OTHER)
        elif form.Mappa.data:
            return RedirectResponse("https://mappa.flyitalyadsb.com", status_code=status.HTTP_303_SEE_OTHER)
        elif form.Report.data:
            return RedirectResponse("/report", status_code=status.HTTP_303_SEE_OTHER)
        elif form.Sito.data:
            return RedirectResponse("https://flyitalyadsb.com", status_code=status.HTTP_303_SEE_OTHER)
        elif form.Grafici.data:
            return RedirectResponse("https://statistiche.flyitalyadsb.com", status_code=status.HTTP_303_SEE_OTHER)
    ricevitore = session.ricevitore
    if ricevitore and not ricevitore.lon:
        flash("MLAT e FEED non sincronizzati, utilizzo la posizione media degli aerei ricevuti")
        # TODO handle this in the template
    return templates.TemplateResponse('index.html',
                                      {"request": request, "form": form, "posizione": posizione, "mio": mio,
                                       "ricevitore": ricevitore})


path = "modules/blueprint/live/templates"


async def get_peer_info(session_db, uuid):
    query = await session_db.execute(select(Ricevitore).filter_by(uuid=uuid))
    ric: Ricevitore = query.scalar_one_or_none()
    return \
        {
            'lat': ric.lat if ric.lat else ric.lat_avg,
            'lon': ric.lon if ric.lon else ric.lon_avg,
            'nome': ric.name if ric.name else ric.uuid
        }


def anonymize_coordinates(item):
    variation = random.uniform(-0.01, 0.01)
    result = []
    for data in item:
        result.append({
            'lat': float(data['lat']) + variation,
            'lon': float(data['lon']) + variation,
            'nome': data['nome']
        })
    return result


async def get_peers_of_ricevitore(session_db, ricevitore_id):
    result = await session_db.execute(
        select(Ricevitore).filter_by(id=ricevitore_id).options(selectinload(Ricevitore.peers)))
    ricevitore = result.scalar_one_or_none()
    return ricevitore.peers


@live_bp.get("/config.js")
async def stazioni(request: Request):
    session_db = request.state.session_db
    session = request.state.session
    ricevitore: Ricevitore = session.ricevitore
    stazione_centrale_data = await get_peer_info(session_db, ricevitore.uuid)
    peers = await get_peers_of_ricevitore(session_db, ricevitore.id)
    stazioni_collegate_data = await asyncio.gather(
        *(get_peer_info(session_db, ricevitore.uuid) for ricevitore in peers)
    )
    stazioni_collegate_data = anonymize_coordinates(stazioni_collegate_data)
    rendered_js = templates.TemplateResponse(
        "config.js.jinja2",
        {
            "request": request,
            "stazioneCentrale": stazione_centrale_data,
            "stazioniCollegate": stazioni_collegate_data
        }, media_type="application/javascript"
    )
    return rendered_js


@live_bp.post("/session/posizione")
async def posizion(request: Request):
    session = request.state.session
    form = await SliderForm.from_formdata(request)
    if await form.validate_on_submit():
        session.posizione = True
        session.raggio = form.raggio.data
        ok = {'data': "success"}
        return ok
    else:
        return Response(status_code=403)


@live_bp.api_route("/session/only_mine", methods=["POST", "GET"])
async def only_mine_func(request: Request, only_mine_data: str | bool = None):
    session = request.state.session
    form = await OnlyMine.from_formdata(request)
    if await form.validate_on_submit():
        only_mine_data = form.only_mine.data
    if only_mine_data is not None:
        live_bp.logger.debug(only_mine_data)
        if only_mine_data == "solo i miei dati":
            session.only_mine = True
        else:
            session.only_mine = False
        ok = {'data': "success"}
        return ok
    else:
        print("err")


@live_bp.get('/selected_page')
async def session_data(request: Request):
    session = request.state.session
    selected_page = {'selected_page': session.selected_page, "filtered": session.search,
                     "sorted": session.sort}
    return selected_page


@live_bp.post('/disattiva/{modalita}')
async def disattiva(request: Request, modalita: str):
    session = request.state.session
    setattr(session, modalita, False)
    ok = {'data': "success"}
    return ok


@live_bp.get("/table")
async def table_pagination_func(request: Request, posizione: str = False, only_mine: str = False, page: int = 1,
                                sort_by: str = "hex", search: str = None):
    session = request.state.session

    user: Ricevitore = session.ricevitore
    if posizione:  # todo gestire internamente la richiesta
        custom_readsb_url = f"http://readsb:30152/?circle={user.lat if user.lat else user.lat_avg},{user.lon if user.lon else user.lon_avg},{int(posizione)}"
        if platform.system() == "Windows":
            custom_readsb_url = f"https://mappa.flyitalyadsb.com/re-api/?circle={user.lat if user.lat else user.lat_avg},{user.lon if user.lon else user.lon_avg},{int(posizione)}"
        async with aiohttp.ClientSession() as session_http:
            data = await query_updater.fetch_data_from_url(live_bp.logger, custom_readsb_url, session_http)
        # print(data["resultCount"])
        aircs = data["aircraft"]
        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts_func=aircs)
    elif only_mine:
        custom_aircrafts = await query_updater.aicrafts_filtered_by_my_receiver(session)
        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts_func=custom_aircrafts)
    else:
        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts_func=query_updater.aircrafts)
    if search:
        print(sliced_aircrafts)
        data_filtered = [row for row in sliced_aircrafts if
                         search in row['hex'] or
                         (row["info"] is not None and row["info"].Registration is not None and search in row[
                             "info"].Registration) or
                         (row.get('flight') is not None and search in row['flight']) or
                         (row.get('squawk') is not None and search in row['squawk']) or
                         (row["info"] is not None and row['info'].Operator is not None and search in row[
                             'info'].Operator)]

        sliced_aircrafts, pagination = await pagination_func(logger=live_bp.logger, page=page,
                                                             aircrafts_func=data_filtered,
                                                             live=False)

    if sort_by == "Registrazione":
        sliced_aircrafts.sort(key=lambda x: x["info"].Registration if x["info"] is not None and x[
            "info"].Registration is not None else "")
    elif sort_by == "Operator":
        sliced_aircrafts.sort(
            key=lambda x: x["info"].Operator if x["info"] is not None and x["info"].Operator is not None else "")
    return templates.TemplateResponse("table.html",
                                      {"request": request, "aircrafts": sliced_aircrafts, "buttons": pagination},
                                      headers={"Cache-Control": "no-store", "Expires": "0"})


@live_bp.get("/data_raw")
def all_aircrafts_raw():
    return query_updater.aircrafts_raw
