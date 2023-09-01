import logging
import time

from sqlalchemy import select
from sqlalchemy.engine import Result

from common_py.common import query_updater, aircraft_cache
from utility.config import PER_PAGE, UPDATE_TOTAL
from utility.model import Aereo, SessionLocal
from utility.type_hint import DbDizionario

session = SessionLocal()


def paginate(page, total, per_page):
    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    # Numero di bottoni da mostrare prima e dopo la pagina corrente
    surrounding_buttons = 2
    buttons = []

    # Inizio e fine dei bottoni
    start_page = max(1, page - surrounding_buttons)
    end_page = min(total_pages, page + surrounding_buttons)

    # Aggiungi il bottone "Precedente" se non siamo nella prima pagina
    if page > 1:
        buttons.append({"label": "Precedente", "page": page - 1})

    for p in range(start_page, end_page + 1):
        buttons.append({"label": str(p), "page": p, "active": p == page})

    # Aggiungi il bottone "Successivo" se non siamo nell'ultima pagina
    if page < total_pages:
        buttons.append({"label": "Successivo", "page": page + 1})

    return buttons


async def pagination_func(logger: logging.Logger, page: int, aircrafts: list = query_updater.aircrafts, live=True):
    total = len(aircrafts)
    logger.debug(f" len aircrafts passed to pagination_func: {len(aircrafts)} ")
    if page != 0:
        start = (page - 1) * PER_PAGE
    else:
        start = 0
    end = start + PER_PAGE
    sliced_aircrafts = aircrafts[start:end]
    if live:
        sliced_aircrafts = await getINFO_or_add_aircraft_total(logger, sliced_aircrafts)
    pagination = paginate(page=page, total=total, per_page=PER_PAGE)
    return sliced_aircrafts, pagination


async def add_aircraft_to_db(aircraft, logger):
    icao = aircraft["hex"]

    if icao.upper() in query_updater.database_open.keys():
        db_data: DbDizionario = query_updater.database_open[icao.upper()]
        reg = db_data.registration
        type = db_data.icaoaircrafttype
        model = db_data.model
        operator = db_data.operator
        serial_number = db_data.serialnumber
        operator_icao = db_data.operatoricao
        session.add(Aereo(icao=icao.upper(), Registration=reg, ICAOTypeCode=type, Type=model, Operator=operator,
                          SerialNumber=serial_number, OperatorIcao=operator_icao))
    else:
        session.add(Aereo(icao=icao.upper()))
    return icao


async def update_cache_for_added_aircrafts(aicraft_da_aggiungere):
    for icao in aicraft_da_aggiungere:
        result: Result = await session.execute(select(Aereo).filter_by(icao=icao.upper()).order_by(Aereo.id.desc()))
        info: Aereo = result.scalars().first()
        aircraft_cache[icao.lower()] = info.repr()


async def getINFO_or_add_aircraft_total(logger: logging.Logger, sliced_aircrafts=None):  # -> List[AircraftData]
    ac_presenti_nel_db = []
    aicraft_da_aggiungere = []
    # print(f"len getINFO_or_add_aircraft_total sliced_aircrafts: {len(sliced_aircrafts)}")
    if sliced_aircrafts:
        aircrafts = sliced_aircrafts
    else:
        aircrafts = query_updater.aircrafts
    # print(f"len getINFO_or_add_aircraft_total aircrafts: {len(aircrafts)}")
    if not query_updater.aircrafts_da_servire[2] and time.time() - query_updater.aircrafts_da_servire[0] > UPDATE_TOTAL:
        query_updater.aircrafts_da_servire[2] = True

        for aircraft in aircrafts:
            icao: str = aircraft["hex"]

            if icao not in aircraft_cache:
                if not icao.upper() in query_updater.icao_presenti_nel_db:
                    await add_aircraft_to_db(aircraft, logger)
                    aicraft_da_aggiungere.append(icao)
                    query_updater.icao_presenti_nel_db.append(icao)
                else:
                    logging.debug(f"{icao} presente nel nostro database ma non nella cache, interroghiamo il ns db")
                    ac_presenti_nel_db.append(icao)
                    aicraft_da_aggiungere.append(icao)

        await session.commit()

        await update_cache_for_added_aircrafts(aicraft_da_aggiungere)

        info_l = await session.execute(select(Aereo).filter(Aereo.icao.in_(ac_presenti_nel_db)))
        info_l = info_l.scalars().all()

        for ac in info_l:
            aircraft_cache[ac.icao.lower()] = ac.repr()
        for aircraft in aircrafts:
            aircraft["info"] = aircraft_cache[aircraft["hex"]]

        query_updater.aircrafts_da_servire[1] = aircrafts
        query_updater.aircrafts_da_servire[0] = time.time()
        query_updater.aircrafts_da_servire[2] = False

        return aircrafts
    else:
        return query_updater.aircrafts_da_servire[1]
