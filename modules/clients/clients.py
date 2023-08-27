import asyncio
import aiofiles
from utility.config import RECEIVERS_JSON, CLIENTS_MLAT_JSON, UPDATE_CLIENTS, CLIENTS_JSON, SYNC_JSON
import json
from common_py.common import query_updater
from utility.model import Ricevitore, SessionLocal
from shapely.geometry import Point, Polygon
import logging
from sqlalchemy import select

logger = logging.getLogger(__name__)
session = SessionLocal()


async def clients():
    logger.info("CLIENTS in partenza!")
    while True:
        await process_clients()
        await asyncio.sleep(UPDATE_CLIENTS)


async def process_clients():
    async with aiofiles.open(RECEIVERS_JSON, "r") as receivers_file:
        content = await receivers_file.read()
        receiver_readsb = json.loads(content)["receivers"]
        async with aiofiles.open(CLIENTS_JSON, "r") as clients_readsb_file:
            content = await clients_readsb_file.read()
            clients_readsb = json.loads(content)["clients"]
            async with aiofiles.open(CLIENTS_MLAT_JSON, "r") as clients_mlat_file:
                content = await clients_mlat_file.read()
                clients_mlat = json.loads(content)
                async with aiofiles.open(SYNC_JSON, "r") as sync_file:
                    content = await sync_file.read()
                    sync_mlat = json.loads(content)
                    for receiver_readsb in receiver_readsb:
                        for client_readsb in clients_readsb:
                            ric_query = await session.execute(select(Ricevitore).filter_by(uuid=client_readsb[0]))
                            ric: Ricevitore = ric_query.scalar_one_or_none()
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
                                if not ric.linked:
                                    for client_mlat in clients_mlat.values():
                                        if client_mlat["uuid"] == client_readsb[0]:
                                            ric.lat = client_mlat["lat"]
                                            ric.lon = client_mlat["lon"]
                                            ric.name = client_mlat["user"]
                                            ric.peers = []
                                            peer_names = [peer for peer in
                                                          sync_mlat[client_mlat["user"]]["peers"].keys()]
                                            all_possible_peers_query = await session.execute(
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

                                    if client_mlat["uuid"] and client_mlat["uuid"][:18] == receiver_readsb[0] == \
                                            client_readsb[0][:18]:
                                        peers = []
                                        peer_names = [peer for peer in sync_mlat[client_mlat["user"]]["peers"].keys()]
                                        all_possible_peers_query = await session.execute(select(Ricevitore).filter(Ricevitore.name.in_(peer_names)))
                                        all_possible_peers = all_possible_peers_query.scalars().all()
                                        peer_dict = {peer.name: peer for peer in all_possible_peers}
                                        for ricevitore_name in peer_names:
                                            peer = peer_dict.get(ricevitore_name)
                                        if peer:
                                            ric.peers.append(peer)
                                        session.add(Ricevitore(
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
                                        session.add(Ricevitore(
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

        await session.commit()
        query = await session.execute(select(Ricevitore))
        query_updater.ricevitori = query


start = (0, 0)

receivers = [(1, 1), (1, 5), (5, 5), (5, 1)]

polygon = Polygon([start] + receivers)
