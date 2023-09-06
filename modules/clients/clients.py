import asyncio
import logging

import aiofiles
import ujson
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from utility.config import RECEIVERS_JSON, CLIENTS_MLAT_JSON, CLIENTS_JSON, SYNC_JSON
from utility.model import Receiver

logger = logging.getLogger(__name__)


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


async def clients(session):
    receiver_readsb, clients_readsb, clients_mlat, sync_mlat = await asyncio.gather(
        read_file(RECEIVERS_JSON),
        read_file(CLIENTS_JSON),
        read_file(CLIENTS_MLAT_JSON),
        read_file(SYNC_JSON)
    )

    # Get existing receivers from database
    ric_query = await session.execute(select(Receiver).options(selectinload(Receiver.peers)))
    ric_dict = {ric.uuid: ric for ric in ric_query.scalars().all()}

    async def add_or_update_receiver(receiver_read, client_read):
        uuid = client_read[0]
        ric = ric_dict.get(uuid)

        # Base data
        base_data = {
            'uuid': uuid,
            'position_counter': receiver_read[1],
            'timed_out_counter': receiver_read[2],
            'lat_min': receiver_read[3],
            'lat_max': receiver_read[4],
            'lon_min': receiver_read[5],
            'lon_max': receiver_read[6],
            'lat_avg': receiver_read[8],
            'lon_avg': receiver_read[9],
            'messagges_per_sec': client_read[4]
        }

        # Update if receiver exists
        if ric:
            for key, value in base_data.items():
                setattr(ric, key, value)
            ric.linked = True
        else:
            session.add(Receiver(**base_data))

        # Additional data from mlat clients
        client_mlat_data = clients_mlat.get(uuid)
        if client_mlat_data:
            ric.lat = client_mlat_data["lat"]
            ric.lon = client_mlat_data["lon"]
            ric.name = client_mlat_data["user"]

            # Peers processing
            peer_names = list(sync_mlat[client_mlat_data["user"]]["peers"].keys())
            peer_query = await session.execute(select(Receiver).filter(Receiver.name.in_(peer_names)))
            peer_dict = {peer.name: peer for peer in peer_query.scalars().all()}
            peers = [peer_dict.get(name) for name in peer_names if peer_dict.get(name) not in ric.peers]

            ric.peers.extend(peers)

    # Processing
    for receiver_read in tqdm(receiver_readsb, desc="Adding CLIENTS to internal db"):
        matched_clients = [client for client in clients_readsb if receiver_read[0] == client[0][:18]]
        for client_read in matched_clients:
            await add_or_update_receiver(receiver_read, client_read)

    # Commit changes
    try:
        await session.commit()
    except Exception as e:
        print(f"Error occurred committing: {e}")
        await session.rollback()

