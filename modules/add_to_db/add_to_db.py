import asyncio
import datetime
import logging

from sqlalchemy import select
from tqdm import tqdm

from common_py.common import query_updater
from common_py.commonLiveReport import getINFO_or_add_aircraft_total
from utility.config import UPDATE_ADD_TO_DB
from utility.model import SessionLocal, Volo
from typing import List

logger = logging.getLogger(__name__)

session_db = SessionLocal()


async def add_to_db(aircraft, now):
    if "squawk" in aircraft.keys():
        volo = Volo(aereo_id=aircraft["info"].id, squawk=aircraft["squawk"], inizio=now,
                    fine=now, traccia_conclusa=False)
    else:
        volo = Volo(aereo_id=aircraft["info"].id, inizio=now,
                    fine=now, traccia_conclusa=False)

    check_or_add_receivers(volo, aircraft)

    session_db.add(volo)


def check_or_add_receivers(volo: Volo, aircraft):
    if "recentReceiverIds" in aircraft.keys() and len(aircraft["recentReceiverIds"]) > 0:
        ricevitori_dict = {ricevitore.uuid[:18]: ricevitore for ricevitore in query_updater.ricevitori}
        for uuid in aircraft["recentReceiverIds"]:
            ricevitore_class = ricevitori_dict.get(uuid)
            if ricevitore_class:
                volo.ricevitore.append(ricevitore_class)
    else:
        logger.debug("recentReceiverIds no in aircraft keys")


async def add_aircrafts_to_db():
    """
    Aggiunge gli aerei al database
    :return:
    """
    logger.info("Aerei_DB in partenza!")
    while True:
        aircrafts = await getINFO_or_add_aircraft_total(logger=logger)
        filtro = [aircraft["info"].id for aircraft in aircrafts]
        volo_query = await session_db.execute(select(Volo).filter(Volo.aereo_id.in_(filtro)).order_by(Volo.id.desc()))
        volo_list: List[Volo] = volo_query.scalars().all()
        volo_dict = {volo.aereo_id: volo for volo in volo_list}
        for aircraft in tqdm(aircrafts, desc="Aggiunta VOLI al db interno"):
            if aircraft["info"].id:
                now = datetime.datetime.fromtimestamp(query_updater.data["now"])
                k = volo_dict.get(aircraft["info"].id)
                if k:
                    check_or_add_receivers(k, aircraft)
                    if now - k.fine > datetime.timedelta(seconds=25 * 60):
                        if k.traccia_conclusa:
                            await add_to_db(aircraft, now)
                        else:
                            k.fine = now
                            k.traccia_conclusa = True
                    else:
                        continue
                else:
                    await add_to_db(aircraft, now)

            else:
                logger.warning(f"no id: {aircraft}")
                print(aircraft)
        try:
            await session_db.commit()
        except Exception as e:
            print(f"Error occurred committing: {e}")
            await session_db.rollback()  # Roll back the transaction in case of errors
        await asyncio.sleep(UPDATE_ADD_TO_DB)
