import datetime
import logging
from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from common_py.common import query_updater
from common_py.commonLiveReport import getINFO_or_add_aircraft_total
from utility.model import Flight, Receiver

logger = logging.getLogger(__name__)


async def add_to_db(session: AsyncSession, receivers_dict: Dict[Receiver.uuid: Receiver], aircraft,
                    now: datetime.datetime):
    if "squawk" in aircraft.keys():
        flight = Flight(aircraft_id=aircraft["info"].id, squawk=aircraft["squawk"], start=now,
                        end=now, ended=False)
    else:
        flight = Flight(aircraft_id=aircraft["info"].id, start=now,
                        end=now, ended=False)

    add_receiver_to_flight(flight, aircraft, receivers_dict)

    session.add(flight)


async def add_aircrafts_to_db(session: AsyncSession):
    aircrafts = await getINFO_or_add_aircraft_total(logger=logger)
    filter = [aircraft["info"].id for aircraft in aircrafts]
    flight_query = await session.execute(
        select(Flight).options(selectinload(Flight.receiver)).filter(Flight.aircraft_id.in_(filter)).order_by(
            Flight.id.desc()))
    flight_list: List[Flight] = flight_query.scalars().all()
    flight_dict = {volo.aircraft_id: volo for volo in flight_list}

    result = await session.execute(select(Receiver))
    receivers = result.scalars().all()
    receivers_dict = {receiver.uuid[:18]: receiver for receiver in receivers}

    for aircraft in tqdm(aircrafts, desc="Adding VOLI to internal db"):
        if aircraft["info"].id:
            now = datetime.datetime.fromtimestamp(query_updater.data["now"])
            flight: Flight = flight_dict.get(aircraft["info"].id)
            if flight:
                add_receiver_to_flight(flight, aircraft, receivers_dict)

                if now - flight.end > datetime.timedelta(seconds=25 * 60):
                    if flight.ended:
                        await add_to_db(session, receivers_dict, aircraft, now)
                    else:
                        flight.end = now
                        flight.ended = True
                else:
                    continue
            else:
                await add_to_db(session, receivers_dict, aircraft, now)

        else:
            logger.warning(f"no id: {aircraft}")
            logger.debug(aircraft)
    try:
        await session.commit()
    except Exception as e:
        print(f"Error occurred committing: {e}")
        await session.rollback()  # Roll back the transaction in case of errors


def add_receiver_to_flight(flight: Flight, aircraft, receivers_dict: Dict[Receiver.uuid: Receiver]):
    if "recentReceiverIds" in aircraft.keys() and len(aircraft["recentReceiverIds"]) > 0:
        for uuid in aircraft["recentReceiverIds"]:
            receiver = receivers_dict.get(uuid)
            if receiver and receiver not in flight.receiver:
                try:
                    flight.receiver.append(receiver)
                except Exception as e:
                    logger.warning(f"errore: {e}")
    else:
        logger.debug("recentReceiverIds no in aircraft keys")
