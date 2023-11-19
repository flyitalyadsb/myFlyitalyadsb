import logging
import time
from typing import List, Dict, Tuple, Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from tqdm import tqdm

from common_py.common import query_updater, aircraft_cache
from utility.config import config
from utility.model import Aircraft
from utility.type_hint import DatabaseDict


def paginate(page, total, per_page) -> List[Dict]:
    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    surrounding_buttons = 2
    buttons = []

    start_page = max(1, page - surrounding_buttons)
    end_page = min(total_pages, page + surrounding_buttons)

    if page > 1:
        buttons.append({"label": "Previous", "page": page - 1})

    for p in range(start_page, end_page + 1):
        buttons.append({"label": str(p), "page": p, "active": p == page, "before": p < page, "after": p > page})

    if page < total_pages:
        buttons.append({"label": "Next", "page": page + 1})

    return buttons


async def pagination_func(
        session_db,
        logger: logging.Logger,
        page: int,
        aircrafts_func: List[Any],
        live=True
) -> Tuple[List[Dict], List[Dict]]:
    total = len(aircrafts_func)
    logger.debug(f" len aircrafts passed to pagination_func: {len(aircrafts_func)} ")
    if page != 0:
        start = (page - 1) * config.per_page
    else:
        start = 0
    end = start + config.per_page
    sliced_aircrafts = aircrafts_func[start:end]
    if live:
        sliced_aircrafts = await get_info_or_add_aircraft_total(session_db, sliced_aircrafts)
    pagination = paginate(page=page, total=total, per_page=config.per_page)
    return sliced_aircrafts, pagination


async def add_aircraft_to_db(aircraft, session_db):
    icao = aircraft["hex"]

    if icao.upper() in query_updater.database_open.keys():
        db_data: DatabaseDict = query_updater.database_open[icao.upper()]
        reg = db_data.registration
        type = db_data.icaoaircrafttype
        model = db_data.model
        operator = db_data.operator
        serial_number = db_data.serialnumber
        operator_icao = db_data.operatoricao
        aircraft_db = Aircraft(icao=icao.upper(), registration=reg, icao_type_code=type, type=model, operator=operator,
                               serial_number=serial_number, operator_icao=operator_icao)
        session_db.add(aircraft_db)
    else:
        aircraft_db = Aircraft(icao=icao.upper())
        session_db.add(aircraft_db)
    return aircraft_db


async def update_cache_for_added_aircrafts(aircrafts_to_add, session_db):
    icaos_upper = [icao.upper() for icao in aircrafts_to_add]
    result: Result = await session_db.execute(
        select(Aircraft).filter(Aircraft.icao.in_(icaos_upper)).order_by(Aircraft.id.desc()))
    all_aircrafts_info = result.scalars().all()

    for info in all_aircrafts_info:
        aircraft_cache[info.icao.lower()] = info.repr()



async def get_info_or_add_aircraft_total(session_db, sliced_aircrafts=None):
    ac_in_db = []
    aircrafts_to_add = []
    if sliced_aircrafts:
        aircrafts = sliced_aircrafts
    else:
        aircrafts = query_updater.aircraft
        query_updater.aircraft_to_be_served[2] = True
    for aircraft in tqdm(aircrafts, desc="Obtaining each aircraft's INFO"):
        icao: str = aircraft["hex"]

        if icao not in aircraft_cache:
            if not icao.upper() in query_updater.icao_in_database:
                await add_aircraft_to_db(aircraft, session_db)
                aircrafts_to_add.append(icao)
                query_updater.icao_in_database.append(icao)
            else:
                logging.debug(f"{icao} in our db but not in the cache, let's query our db")
                ac_in_db.append(icao)
                aircrafts_to_add.append(icao)

    await session_db.commit()

    await update_cache_for_added_aircrafts(aircrafts_to_add, session_db)

    info_l = await session_db.execute(select(Aircraft).filter(Aircraft.icao.in_(ac_in_db)))
    info_l = info_l.scalars().all()

    for ac in info_l:
        aircraft_cache[ac.icao.lower()] = ac.repr()
    for aircraft in aircrafts:
        aircraft["info"] = aircraft_cache[aircraft["hex"]]

    query_updater.aircraft_to_be_served[0] = time.time()
    query_updater.aircraft_to_be_served[1] = aircrafts
    return aircrafts
