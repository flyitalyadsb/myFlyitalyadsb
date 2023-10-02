import asyncio
import logging
import random
from typing import List

from fastapi import APIRouter, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.responses import RedirectResponse

from common_py.common import flash, get_flashed_message
from common_py.commonLiveReport import pagination_func, query_updater
from modules.blueprint.utility.calculate_distance import haversine_distance
from utility.forms import MenuForm, SliderForm, OnlyMine
from utility.model import Receiver
from utility.model import SessionData

live_bp = APIRouter()
path = "modules/blueprint/live/templates"
templates = Jinja2Templates(directory=path)
templates.env.globals["get_flashed_messages"] = get_flashed_message

live_bp.logger = logging.getLogger(__name__)


@live_bp.api_route("/", methods=["GET", "POST"], tags=["users"])
async def index(request: Request):
    session: SessionData = request.state.session
    form = await MenuForm.from_formdata(request)
    position = await SliderForm.from_formdata(request)
    mine = await OnlyMine.from_formdata(request)
    if await form.validate_on_submit():
        if form.my_map.data:
            return RedirectResponse("/map", status_code=status.HTTP_303_SEE_OTHER)
        elif form.map.data:
            return RedirectResponse("https://mappa.flyitalyadsb.com", status_code=status.HTTP_303_SEE_OTHER)
        elif form.report.data:
            return RedirectResponse("/report", status_code=status.HTTP_303_SEE_OTHER)
        elif form.site.data:
            return RedirectResponse("https://flyitalyadsb.com", status_code=status.HTTP_303_SEE_OTHER)
        elif form.graphs.data:
            return RedirectResponse("https://statistiche.flyitalyadsb.com", status_code=status.HTTP_303_SEE_OTHER)
    receiver = session.receiver
    if receiver and not receiver.lon:
        flash(request, "MLAT and FEED not synced, we use the average position of received aircraft")
    return templates.TemplateResponse('index.html',
                                      {"request": request, "form": form, "position": position, "mio": mine,
                                       "receiver": receiver})


async def get_peer_info(session_db, uuid):
    query = await session_db.execute(select(Receiver).filter_by(uuid=uuid))
    ric: Receiver = query.scalar_one_or_none()
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


async def get_peers_of_receiver(session_db, receiver_id):
    result = await session_db.execute(
        select(Receiver).filter_by(id=receiver_id).options(selectinload(Receiver.peers)))
    receiver = result.scalar_one_or_none()
    return receiver.peers


def get_near_aircraft(radius: int, aircraft: List, receiver: Receiver) -> List:
    result = []
    for airc in aircraft:
        lat, lon = airc.get("lat"), airc.get("lon")
        if lat and lon:
            distance = haversine_distance(receiver.lat, receiver.lon, lat, lon)
            if distance < radius:
                result.append(airc)
    return result


@live_bp.get("/config.js")
async def stations(request: Request):
    session_db = request.state.session_db
    session = request.state.session
    receiver: Receiver = session.receiver
    my_receiver = await get_peer_info(session_db, receiver.uuid)
    peers = await get_peers_of_receiver(session_db, receiver.id)
    synced_receivers = await asyncio.gather(
        *(get_peer_info(session_db, receiver.uuid) for receiver in peers)
    )
    synced_receivers = anonymize_coordinates(synced_receivers)
    rendered_js = templates.TemplateResponse(
        "config.js.jinja2",
        {
            "request": request,
            "my_receiver": my_receiver,
            "synced_receivers": synced_receivers
        }, media_type="application/javascript"
    )
    return rendered_js


@live_bp.get('/selected_page')
async def session_data(request: Request):
    session = request.state.session
    selected_page = {'selected_page': session.selected_page, "filtered": session.search,
                     "sorted": session.sort}
    return selected_page


def matches_search_criteria(row, search, where):
    if where == "everywhere":
        return (search in row.get('hex', '')) or \
            (row.get("info") and row["info"].registration is not None and search in row["info"].registration) or \
            (row.get("info") and row["info"].operator is not None and search in row["info"].operator) or \
            (search in row.get('flight', '')) or \
            (search in row.get('squawk', ''))
    elif where == "hex":
        return search in row.get('hex', '')
    elif where == "registration":
        return row.get("info") and row["info"].registration is not None and search in row["info"].registration
    elif where == "operator":
        return row.get("info") and row["info"].operator is not None and search in row["info"].operator
    elif where == "flight":
        return search in row.get('flight', '')
    elif where == "squawk":
        return search in row.get('squawk', '')
    return False


@live_bp.get("/table")
async def table_pagination_func(request: Request, position: str = False, only_mine: str = False, page: int = 1,
                                sort_by: str = "hex", search: str = None, where: str = None):
    session = request.state.session
    session_db = request.state.session_db
    receiver: Receiver = session.receiver
    if position:
        aircs = get_near_aircraft(int(position), query_updater.aircraft, receiver)
        if not aircs:
            return templates.TemplateResponse("table.html",
                                              {"request": request, "aircrafts": aircs,
                                               "buttons": []},
                                              headers={"Cache-Control": "no-store", "Expires": "0"})
        sliced_aircrafts, pagination = await pagination_func(session_db, logger=live_bp.logger, page=page,
                                                             aircrafts_func=aircs)
    elif only_mine:
        custom_aircrafts = await query_updater.aicrafts_filtered_by_my_receiver(session)
        sliced_aircrafts, pagination = await pagination_func(session_db, logger=live_bp.logger, page=page,
                                                             aircrafts_func=custom_aircrafts)
    else:
        sliced_aircrafts, pagination = await pagination_func(session_db, logger=live_bp.logger, page=page,
                                                             aircrafts_func=query_updater.aircraft)
    if search:
        data_filtered = [row for row in sliced_aircrafts if matches_search_criteria(row, search, where)]

        sliced_aircrafts, pagination = await pagination_func(session_db, logger=live_bp.logger, page=page,
                                                             aircrafts_func=data_filtered,
                                                             live=False)
    if sort_by == "registration":
        sliced_aircrafts.sort(key=lambda x: x["info"].registration if x["info"] is not None and x[
            "info"].registration is not None else "")
    elif sort_by == "operator":
        sliced_aircrafts.sort(
            key=lambda x: x["info"].operator if x["info"] is not None and x["info"].operator is not None else "")
    elif sort_by == "flight":
        sliced_aircrafts.sort(
            key=lambda x: x["flight"] if x.get("flight") is not None else "")
    elif sort_by == "squawk":
        sliced_aircrafts.sort(
            key=lambda x: x["squawk"] if x.get("squawk") is not None else "")
    return templates.TemplateResponse("table.html",
                                      {"request": request, "aircrafts": sliced_aircrafts, "buttons": pagination,
                                       "receiver": receiver}, headers={"Cache-Control": "no-store", "Expires": "0"})


@live_bp.get("/data_raw")
def all_aircrafts_raw():
    return query_updater.aircraft_raw
