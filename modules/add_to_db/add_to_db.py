import datetime
import logging
import os
from typing import List, Dict

import psutil
from sqlalchemy import select, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from common_py.common import query_updater
from common_py.commonLiveReport import get_info_or_add_aircraft_total
from utility.model import Flight, Receiver

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)

async def real_add_aircraft_to_db(session: AsyncSession, receivers_dict: Dict[str, Receiver], aircraft, now: datetime.datetime):
    if "squawk" in aircraft.keys():
        flight = Flight(aircraft_id=aircraft["info"].id, squawk=aircraft["squawk"], start=now,
                        end=now, ended=False)
    else:
        flight = Flight(aircraft_id=aircraft["info"].id, start=now,
                        end=now, ended=False)

    add_receivers_to_flight(flight, aircraft, receivers_dict)

    session.add(flight)


def monitor_usage():
    pid = os.getpid()
    process = psutil.Process(pid)

    # Calcola l'utilizzo della memoria e della CPU
    memory_use = process.memory_info().rss  # in bytes
    cpu_use = process.cpu_percent(interval=1)

    print(f"Memory Usage: {memory_use / (1024 * 1024):.2f} MB, CPU Usage: {cpu_use}%")


async def add_aircrafts_to_db(session: AsyncSession):
    print("Add aircraft to db started")
    aircrafts = await get_info_or_add_aircraft_total(session)
    filter = [aircraft["info"].id for aircraft in aircrafts]
    monitor_usage()
    flight_query = await session.execute(
        select(Flight).options(selectinload(Flight.receiver)).filter(Flight.aircraft_id.in_(filter)).order_by(
            Flight.id.desc()))
    flight_list: Sequence[Flight] = flight_query.scalars().all()
    flight_dict = {flight.aircraft_id: flight for flight in flight_list}
    monitor_usage()
    result = await session.execute(select(Receiver))
    monitor_usage()
    receivers = result.scalars().all()
    receivers_dict = {receiver.uuid[:18]: receiver for receiver in receivers}

    for aircraft in tqdm(aircrafts, desc="Adding FLIGHTS to internal db"):
        monitor_usage()
        if aircraft["info"].id:
            now = datetime.datetime.fromtimestamp(query_updater.data["now"])
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
                    continue
            else:
                await real_add_aircraft_to_db(session, receivers_dict, aircraft, now)

        else:
            logger.warning(f"no id: {aircraft}")
            logger.debug(aircraft)
    try:
        await session.commit()
    except Exception as e:
        print(f"Error occurred committing: {e}")
        await session.rollback()  # Roll back the transaction in case of errors


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
