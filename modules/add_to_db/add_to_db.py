import asyncio
import datetime
from utility.model import SessionLocal, Volo
from common_py.commonLiveReport import getINFO_or_add_aircraft_total
from common_py.common import query_updater
import logging
from tqdm import tqdm
from sqlalchemy import select
logger = logging.getLogger(__name__)

session =  SessionLocal()
async def add_to_db(aircraft, now):
    if "squawk" in aircraft.keys():
        volo = Volo(aereo_id=aircraft["info"].id, squawk=aircraft["squawk"], inizio=now.timestamp(),
                    fine=now.timestamp(), traccia_conclusa=False)
    else:
        volo = Volo(aereo_id=aircraft["info"].id, inizio=now.timestamp(),
                    fine=now.timestamp(), traccia_conclusa=False)

    if "recentReceiverIds" in aircraft.keys() and len(aircraft["recentReceiverIds"]) > 0:
        ricevitori_dict = {ricevitore.uuid: ricevitore for ricevitore in query_updater.ricevitori}
        for uuid in aircraft["recentReceiverIds"]:
            ricevitore_class = ricevitori_dict.get(uuid)
            if ricevitore_class:
                volo.ricevitori.append(ricevitore_class)

    else:
        logger.debug("recentReceiverIds no in aircraft keys")

    session.add(volo)

async def add_aircrafts_to_db():
    """
    Aggiunge gli aerei al database
    :return:
    """
    logger.info("Aerei_DB in partenza!")
    while True:
        aircrafts = await getINFO_or_add_aircraft_total(logger=logger)
        for aircraft in tqdm(aircrafts, desc="Aggiunta aerei al db interno"):
            if aircraft["info"].id:
                now = datetime.datetime.fromtimestamp(query_updater.data["now"])
                k = await session.execute(select(Volo).filter_by(aereo_id=aircraft["info"].id).order_by(Volo.id.desc()))
                k = k.scalar_one_or_none()
                if k:
                    if now - datetime.datetime.fromtimestamp(float(k.fine)) > datetime.timedelta(seconds=25 * 60):
                        if k.traccia_conclusa:
                            await add_to_db(aircraft, now)
                        else:
                            k.fine = now.timestamp()
                            k.traccia_conclusa = True
                    else:
                        continue
                else:
                    await add_to_db(aircraft, now)

            else:
                logger.warning(f"no id: {aircraft}")
                print(aircraft)
        await session.commit()
        await asyncio.sleep(5)
