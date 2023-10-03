import datetime
import gzip
import os

from orjson import orjson
from sqlalchemy import Result, select
from common_py.commonLiveReport import add_aircraft_to_db
from utility.model import Flight, SessionLocal, Aircraft

dir = 'F:/globe_history_prova/'
BATCH_SIZE = 1000
session = SessionLocal()


async def convert_globe_to_db():
    flights_to_add = []
    for year in os.scandir(dir):
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
