import datetime
import logging

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from tqdm import tqdm

from common_py.common import query_updater
from common_py.commonLiveReport import getINFO_or_add_aircraft_total
from utility.model import Volo, Ricevitore
from typing import List

logger = logging.getLogger(__name__)


async def add_to_db(session,ricevitori_dict, aircraft, now):
    if "squawk" in aircraft.keys():
        volo = Volo(aereo_id=aircraft["info"].id, squawk=aircraft["squawk"], inizio=now,
                    fine=now, traccia_conclusa=False)
    else:
        volo = Volo(aereo_id=aircraft["info"].id, inizio=now,
                    fine=now, traccia_conclusa=False)

    if "recentReceiverIds" in aircraft.keys() and len(aircraft["recentReceiverIds"]) > 0:
        for uuid in aircraft["recentReceiverIds"]:
            ricevitore_class = ricevitori_dict.get(uuid)
            if ricevitore_class and ricevitore_class not in volo.ricevitore:
                try:
                    volo.ricevitore.append(ricevitore_class)
                except Exception as e:
                    logger.warning(f"inside {e}")
    else:
        logger.debug("recentReceiverIds no in aircraft keys")

    session.add(volo)


async def add_aircrafts_to_db(session):
    """
    Aggiunge gli aerei al database
    :return:
    """

    aircrafts = await getINFO_or_add_aircraft_total(logger=logger)
    filtro = [aircraft["info"].id for aircraft in aircrafts]
    volo_query = await session.execute(select(Volo).options(selectinload(Volo.ricevitore)).filter(Volo.aereo_id.in_(filtro)).order_by(Volo.id.desc()))
    volo_list: List[Volo] = volo_query.scalars().all()
    volo_dict = {volo.aereo_id: volo for volo in volo_list}

    result = await session.execute(select(Ricevitore))
    ricevitori = result.scalars().all()
    ricevitori_dict = {ricevitore.uuid[:18]: ricevitore for ricevitore in ricevitori}

    for aircraft in tqdm(aircrafts, desc="Aggiunta VOLI al db interno"):
        if aircraft["info"].id:
            now = datetime.datetime.fromtimestamp(query_updater.data["now"])
            k = volo_dict.get(aircraft["info"].id)
            if k:
                if "recentReceiverIds" in aircraft.keys() and len(aircraft["recentReceiverIds"]) > 0:
                    for uuid in aircraft["recentReceiverIds"]:
                        ricevitore = ricevitori_dict.get(uuid)
                        if ricevitore and ricevitore not in k.ricevitore:
                            try:
                                k.ricevitore.append(ricevitore)
                            except Exception as e:
                                logger.warning(f"errore: {e}")
                else:
                    logger.debug("recentReceiverIds no in aircraft keys")
                if now - k.fine > datetime.timedelta(seconds=25 * 60):
                    if k.traccia_conclusa:
                        await add_to_db(session, ricevitori_dict, aircraft, now)
                    else:
                        k.fine = now
                        k.traccia_conclusa = True
                else:
                    continue
            else:
                await add_to_db(session, ricevitori_dict, aircraft, now)

        else:
            logger.warning(f"no id: {aircraft}")
            print(aircraft)
    try:
        await session.commit()
    except Exception as e:
        print(f"Error occurred committing: {e}")
        await session.rollback()  # Roll back the transaction in case of errors
