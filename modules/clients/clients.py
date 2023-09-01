import asyncio
import aiofiles
from sqlalchemy.orm import selectinload

from utility.config import RECEIVERS_JSON, CLIENTS_MLAT_JSON, UPDATE_CLIENTS, CLIENTS_JSON, SYNC_JSON
import ujson
from common_py.common import query_updater
from utility.model import Ricevitore, SessionLocal
from shapely.geometry import Point, Polygon
import logging
from sqlalchemy import select
from tqdm import tqdm

logger = logging.getLogger(__name__)
session_db = SessionLocal()
from typing import List, Dict


async def clients():
    logger.info("CLIENTS in partenza!")
    while True:
        await process_clients()
        await asyncio.sleep(UPDATE_CLIENTS)


async def read_file(filename):
    async with aiofiles.open(filename, "r") as file:
        data = await file.read()

        parsed_data = ujson.loads(data)
        if filename == RECEIVERS_JSON:
            return parsed_data["receivers"]
        elif filename == CLIENTS_JSON:
            return parsed_data["clients"]
        else:
            return parsed_data


async def process_clients():
    receiver_readsb, clients_readsb, clients_mlat, sync_mlat = await asyncio.gather(
        read_file(RECEIVERS_JSON),
        read_file(CLIENTS_JSON),
        read_file(CLIENTS_MLAT_JSON),
        read_file(SYNC_JSON)
    )
    ric_query = await session_db.execute(select(Ricevitore).options(selectinload(Ricevitore.peers)))
    ric_list: List[Ricevitore] = ric_query.scalars().all()
    ric_dict = {ric.uuid: ric for ric in ric_list}
    for receiver_readsb in tqdm(receiver_readsb, desc="Aggiunta CLIENT al db interno"):
        for client_readsb in clients_readsb:
            if receiver_readsb[0] == client_readsb[0][:18]:
                ric = ric_dict.get(client_readsb[0])
                if ric:
                    ric.position_counter = receiver_readsb[1]
                    ric.timed_out_counter = receiver_readsb[2]
                    ric.lat_min = receiver_readsb[3]
                    ric.lat_max = receiver_readsb[4]
                    ric.lon_min = receiver_readsb[5]
                    ric.lon_max = receiver_readsb[6]
                    ric.lat_avg = receiver_readsb[8]
                    ric.lon_avg = receiver_readsb[9]
                    # ric.ip = str(client_readsb[1].split("port")[0].replace(" ", "")),
                    ric.messaggi_al_sec = client_readsb[4]
                    for client_mlat in clients_mlat.values():
                        if client_mlat["uuid"] and (client_mlat["uuid"] == client_readsb[0] or client_mlat["uuid"][0] == client_readsb[0]):
                            ric.lat = client_mlat["lat"]
                            ric.lon = client_mlat["lon"]
                            ric.name = client_mlat["user"]
                            ric.peers = []
                            peer_names = [peer for peer in sync_mlat[client_mlat["user"]]["peers"].keys()]
                            all_possible_peers_query = await session_db.execute(
                                select(Ricevitore).filter(Ricevitore.name.in_(peer_names)))
                            all_possible_peers = all_possible_peers_query.scalars().all()

                            peer_dict = {peer.name: peer for peer in all_possible_peers}
                            for ricevitore_name in peer_names:
                                peer = peer_dict.get(ricevitore_name)
                                if peer:
                                    ric.peers.append(peer)
                            ric.linked = True
                else:
                    process = True
                    for client_mlat in clients_mlat.values():


                        if client_mlat["uuid"] and (
                                client_mlat["uuid"][0][:18] == receiver_readsb[0] == client_readsb[0][:18] or
                                client_mlat["uuid"][:18] == receiver_readsb[0] == client_readsb[0][:18]
                        ):
                            print(client_mlat["user"])
                            peers = []
                            peer_names = [peer for peer in sync_mlat[client_mlat["user"]]["peers"].keys()]
                            all_possible_peers_query = await session_db.execute(
                                select(Ricevitore).filter(Ricevitore.name.in_(peer_names)))

                            all_possible_peers = all_possible_peers_query.scalars().all()
                            peer_dict = {peer.name: peer for peer in all_possible_peers}
                            for ricevitore_name in peer_names:
                                peer = peer_dict.get(ricevitore_name)
                            if peer:
                                print(peer)
                                ric.peers.append(peer)
                            session_db.add(Ricevitore(
                                linked=True,
                                lat=client_mlat["lat"],
                                lon=client_mlat["lon"],
                                name=client_mlat["user"],
                                uuid=client_readsb[0],
                                position_counter=receiver_readsb[1],
                                timed_out_counter=receiver_readsb[2],
                                lat_min=receiver_readsb[3],
                                lat_max=receiver_readsb[4],
                                lon_min=receiver_readsb[5],
                                lon_max=receiver_readsb[6],
                                lat_avg=receiver_readsb[8],
                                lon_avg=receiver_readsb[9],
                                # ip=str(client_readsb[1].split("port")[0].replace(" ", "")),
                                messaggi_al_sec=client_readsb[4],
                                peers=peers
                            ))
                            process = False
                    if process:
                        if receiver_readsb[0] == client_readsb[0][:18]:
                            session_db.add(Ricevitore(
                                uuid=client_readsb[0],
                                position_counter=receiver_readsb[1],
                                timed_out_counter=receiver_readsb[2],
                                lat_min=receiver_readsb[3],
                                lat_max=receiver_readsb[4],
                                lon_min=receiver_readsb[5],
                                lon_max=receiver_readsb[6],
                                lat_avg=receiver_readsb[8],
                                lon_avg=receiver_readsb[9],
                                # ip=str(client_readsb[1].split("port")[0].replace(" ", "")),
                                messaggi_al_sec=client_readsb[4]
                            ))

    await session_db.commit()
    result = await session_db.execute(select(Ricevitore))
    ricevitori = result.scalars().all()
    query_updater.ricevitori = ricevitori



