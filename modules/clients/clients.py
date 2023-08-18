import asyncio
import aiofiles
import aiohttp
import requests

from utility.config import RECEIVERS_JSON, CLIENTS_MLAT_JSON, UPDATE_CLIENTS
import json
from common_py.common import query_updater
from utility.model import Ricevitore, db
from shapely.geometry import Point, Polygon
import logging

logger = logging.getLogger()


async def clients():
    logger.info("CLIENTS in partenza!")
    while True:
        await process_clients()
        await asyncio.sleep(UPDATE_CLIENTS)


async def process_clients():
    async with aiofiles.open(RECEIVERS_JSON, "r") as receivers_file:
        content = await receivers_file.read()
        data_receivers = json.loads(content)["receivers"]
        async with aiofiles.open(CLIENTS_MLAT_JSON, "r") as clients_mlat_file:
            content = await clients_mlat_file.read()
            clients_mlat = json.loads(content)
            for ricevitore in data_receivers:
                ric = Ricevitore.query.filter_by(uuid=ricevitore[0]).first()
                if ric:
                    ric.position_counter = ricevitore[1]
                    ric.timed_out_counter = ricevitore[2]
                    ric.lat_min = ricevitore[3]
                    ric.lat_max = ricevitore[4]
                    ric.lon_min = ricevitore[5]
                    ric.lon_max = ricevitore[6]
                    ric.lat_avg = ricevitore[8]
                    ric.lon_avg = ricevitore[9]
                    if not ric.linked:
                        for client in clients_mlat.values():
                            if client["uuid"] == ricevitore[0][0]:
                                ric.lat = client["lat"]
                                ric.lon = client["lon"]
                                ric.name = client["user"]
                                ric.linked = True

                else:
                    process = True
                    for client in clients_mlat.values():
                        if client["uuid"] == ricevitore[0]:
                            db.session.add(Ricevitore(
                                link=True,
                                lat=client["lat"],
                                lon=client["lon"],
                                name=client["user"],
                                uuid=ricevitore[0],
                                position_counter=ricevitore[1],
                                timed_out_counter=ricevitore[2],
                                lat_min=ricevitore[3],
                                lat_max=ricevitore[4],
                                lon_min=ricevitore[5],
                                lon_max=ricevitore[6],
                                lat_avg=ricevitore[8],
                                lon_avg=ricevitore[9]
                            ))
                            process = False
                    if process:
                        db.session.add(Ricevitore(
                            uuid=ricevitore[0],
                            position_counter=ricevitore[1],
                            timed_out_counter=ricevitore[2],
                            lat_min=ricevitore[3],
                            lat_max=ricevitore[4],
                            lon_min=ricevitore[5],
                            lon_max=ricevitore[6],
                            lat_avg=ricevitore[8],
                            lon_avg=ricevitore[9]
                        ))
    db.session.commit()
    query_updater.ricevitori = Ricevitore.query.all()



start = (0, 0)

receivers = [(1, 1), (1, 5), (5, 5), (5, 1)]

polygon = Polygon([start] + receivers)




