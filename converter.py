import asyncio
import datetime
import gzip
import os

from orjson import orjson
from sqlalchemy import Result, select
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

from common_py.commonLiveReport import add_aircraft_to_db
from utility.model import Flight, SessionLocal, Aircraft
import aiosqlite

dir_globe_history = '/globe_history/'
BATCH_SIZE = 1000
session: AsyncSession = SessionLocal()
path_basestation_vrs = "/db/BaseStation.sqb"


async def convert_globe_to_db():
    flights_to_add = []
    for year in os.scandir(dir_globe_history):
        for month in os.scandir(year.path):
            for day in os.scandir(month.path):
                for subclasses in os.scandir(day.path):
                    for file in os.scandir(subclasses.path):
                        with gzip.open(file, 'rb') as json_file:
                            try:
                                data = orjson.loads(json_file.read())
                            except:
                                pass
                        icao = data["icao"]
                        timeZero = data['timestamp']
                        trace = data['trace']
                        ftime = datetime.datetime.fromtimestamp(timeZero)
                        ltime = datetime.datetime.fromtimestamp(timeZero + trace[-1][0])

                        if isinstance(trace[0][8], dict):
                            fkeys = trace[0][8].keys()
                        else:
                            fkeys = []
                        if isinstance(trace[-1][8], dict):
                            lkeys = trace[-1][8].keys()
                        else:
                            lkeys = []

                        if "squawk" in fkeys:
                            squawk = trace[0][8]["squawk"]
                        elif "squawk" in lkeys:
                            squawk = trace[-1][8]["squawk"]
                        else:
                            squawk = ""
                        result: Result = await session.execute(
                            select(Aircraft).filter_by(icao=icao.upper()).order_by(Aircraft.id.desc()))
                        info: Aircraft = result.scalars().first()
                        if not info:
                            info = await add_aircraft_to_db({"hex": icao}, session)
                        flight = Flight(aircraft_id=info.id, squawk=squawk, start=ftime.timestamp(),
                                        end=ltime.timestamp(), ended=True)
                        flights_to_add.append(flight)

                        if len(flights_to_add) >= BATCH_SIZE:
                            session.bulk_save_objects(flights_to_add)
                            await session.commit()
                            flights_to_add.clear()


async def populate_model_from_db():
    async with aiosqlite.connect(path_basestation_vrs) as db:
        async with db.cursor() as cursor:
            # Fetch data from Aircraft table
            await cursor.execute(
                "SELECT ModeS, Registration, ICAOTypeCode, Type, OperatorFlagCode, SerialNo, RegisteredOwners FROM Aircraft")
            aircraft_rows = await cursor.fetchall()
            # Convert data to Aircraft model and commit in batches
            aircraft_objects = [
                Aircraft(icao=row[0], registration=row[1], icao_type_code=row[2], type=row[3],
                         operator_icao=row[4], serial_number=row[5], operator=row[6])
                for row in tqdm(aircraft_rows, desc="Adding Aircraft")]
    return aircraft_objects


async def main():
    if True:
        aircraft_objects = await populate_model_from_db()
        session: AsyncSession = SessionLocal()
        for batch_start in range(0, len(aircraft_objects), BATCH_SIZE):
            for flight in aircraft_objects:
                session.add(flight)
            await session.commit()
    else:
        await convert_globe_to_db()


asyncio.run(main())

"""
        #for batch_start in range(0, len(flight_objects), BATCH_SIZE):
        #    for flight in flight_objects:
        #        session.add(flight)
        #    await session.commit()
        
TODO
            # Fetch data from Flights table
            await cursor.execute(
                "SELECT FlightID, AircraftID, StartTime, EndTime, LastSquawk FROM Flights")
            flight_rows = await cursor.fetchall()

            # Convert data to Flight model and commit in batches
            flight_objects = [Flight(aircraft_id=row[1], start=row[2], end=row[3], squawk=str(row[4]))
                              for row in tqdm(flight_rows, desc="Adding FLIGHTS")]
"""
