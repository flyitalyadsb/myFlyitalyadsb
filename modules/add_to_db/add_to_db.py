import datetime
import logging
from typing import List, Dict

from sqlalchemy import select, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from common_py.common import query_updater
from common_py.commonLiveReport import get_info_or_add_aircraft_total
from utility.model import Flight, Receiver

logger = logging.getLogger(__name__)


async def real_add_aircraft_to_db(session: AsyncSession, receivers_dict: Dict[str, Receiver], aircraft, now: datetime.datetime):
    if "squawk" in aircraft.keys():
        flight = Flight(aircraft_id=aircraft["info"].id, squawk=aircraft["squawk"], start=now,
                        end=now, ended=False)
    else:
        flight = Flight(aircraft_id=aircraft["info"].id, start=now,
                        end=now, ended=False)

    add_receivers_to_flight(flight, aircraft, receivers_dict)

    session.add(flight)


BATCH_SIZE = 500  # You can adjust this based on your needs


async def process_batch(session: AsyncSession, batch_aircrafts, receivers_dict, now):
    aircraft_ids = [aircraft["info"].id for aircraft in batch_aircrafts]

    flight_query = await session.execute(
        select(Flight).options(selectinload(Flight.receiver)).filter(Flight.aircraft_id.in_(aircraft_ids)).order_by(
            Flight.id.desc())
    )
    flight_list: Sequence[Flight] = flight_query.scalars().all()
    flight_dict = {flight.aircraft_id: flight for flight in flight_list}

    for aircraft in batch_aircrafts:
        if aircraft["info"].id:
            flight: Flight = flight_dict.get(aircraft["info"].id)
            if flight:
                add_receivers_to_flight(flight, aircraft, receivers_dict)

                if now - flight.end > datetime.timedelta(seconds=25 * 60):
                    if flight.ended:
                        await real_add_aircraft_to_db(session, receivers_dict, aircraft, now)
                    else:
                        flight.end = now
                        flight.ended = True
            else:
                await real_add_aircraft_to_db(session, receivers_dict, aircraft, now)

        else:
            logger.warning(f"no id: {aircraft}")
            logger.debug(aircraft)

    try:
        await session.commit()
    except Exception as e:
        print(f"Error occurred committing: {e}")
        await session.rollback()


async def add_aircrafts_to_db(session: AsyncSession):
    now = datetime.datetime.fromtimestamp(query_updater.data["now"])
    aircrafts = await get_info_or_add_aircraft_total(session)

    result = await session.execute(select(Receiver))
    receivers = result.scalars().all()
    receivers_dict = {receiver.uuid[:18]: receiver for receiver in receivers}

    # Split aircraft into batches and process each batch
    for i in tqdm(range(0, len(aircrafts), BATCH_SIZE), desc="Adding FLIGHTS to internal db"):
        batch_aircrafts = aircrafts[i:i + BATCH_SIZE]
        await process_batch(session, batch_aircrafts, receivers_dict, now)


def add_receivers_to_flight(flight: Flight, aircraft, receivers_dict: Dict[str, Receiver]):
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
