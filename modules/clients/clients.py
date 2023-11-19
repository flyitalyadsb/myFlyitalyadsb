import asyncio
import datetime
import logging
import re
import socket

import aiofiles
import orjson
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from utility.config import config
from utility.model import Receiver

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)

def remove_duplicates(key, data):
    if key not in data:
        raise ValueError(f'The key "{key}" doesn\'t exists.')

    unique_dict = {}
    for item in data[key]:
        item_key = item[0]
        if item_key not in unique_dict:
            unique_dict[item_key] = item[1:]
    data[key] = [[item_key] + values for item_key, values in unique_dict.items()]

    return data


async def read_file(filename):
    async with aiofiles.open(filename, "r") as file:
        data = await file.read()

        parsed_data = orjson.loads(data)
        if filename == config.receiver_json:
            parsed_data = remove_duplicates("receivers", parsed_data)
            return parsed_data["receivers"]
        elif filename == config.clients_json:
            parsed_data = remove_duplicates("clients", parsed_data)
            return parsed_data["clients"]
        else:
            return parsed_data


def remove_mlat_duplicates(general_dict: dict):
    seen = set()
    result = {}

    for key, value in general_dict.items():
        if isinstance(value["uuid"], list) and value["uuid"][0] not in seen:
            seen.add(value["uuid"][0])
            result[key] = value
        elif not isinstance(value["uuid"], list) and value["uuid"] not in seen:
            seen.add(value["uuid"])
            result[key] = value

    return result


def convert_to_ip(input_string):
    ip = "0.0.0.0"
    if input_string in ["mlat-server"]:
        return ip
    ip_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', input_string)
    hostname_match = re.search(r'\b\w+\.\w+\b', input_string)
    if ip_match:
        ip = ip_match.group(0)
        logger.debug(f"IP found: {ip}")
    elif hostname_match:
        hostname = hostname_match.group(0)
        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            logger.debug(f"No ip found for hostname: {hostname}")
    else:
        logger.warning("No IP address or hostname found")

    return ip


async def clients(session):
    logger.info("Clients started")
    receivers_readsb, clients_readsb, clients_mlat, sync_mlat = await asyncio.gather(
        read_file(config.receiver_json),
        read_file(config.clients_json),
        read_file(config.clients_mlat_json),
        read_file(config.sync_json)
    )
    clients_mlat = remove_mlat_duplicates(clients_mlat)

    # Get existing receivers from database
    ric_query = await session.execute(select(Receiver).options(selectinload(Receiver.peers)))
    ric_dict = {ric.uuid: ric for ric in ric_query.scalars().all()}

    async def add_or_update_receiver(receiver_readsb, client_readsb):
        try:
            uuid = client_readsb[0]
            ric: Receiver = ric_dict.get(uuid)

            # Base data
            base_data = {
                'last_seen': datetime.datetime.now(),
                'uuid': uuid,
                'position_counter': receiver_readsb[1],
                'timed_out_counter': receiver_readsb[2],
                'lat_min': receiver_readsb[3],
                'lat_max': receiver_readsb[4],
                'lon_min': receiver_readsb[5],
                'lon_max': receiver_readsb[6],
                'lat_avg': receiver_readsb[8],
                'lon_avg': receiver_readsb[9],
                'messagges_per_sec': client_readsb[4],
                'ip': convert_to_ip(client_readsb[1])
            }

            # Update if receiver exists
            if ric:
                for key, value in base_data.items():
                    setattr(ric, key, value)
            else:
                ric = Receiver(**base_data)
                session.add(ric)

            # Additional data from mlat clients
            client_mlat_data = next(
                (c for c in clients_mlat.values() if c["uuid"] and (c["uuid"] == uuid or uuid in c["uuid"])), None)

            if client_mlat_data:
                ric.lat = client_mlat_data["lat"]
                ric.lon = client_mlat_data["lon"]
                ric.alt = client_mlat_data["alt"]
                ric.name = client_mlat_data["user"]

                # Peers processing
                peer_names = list(sync_mlat[client_mlat_data["user"]]["peers"].keys())
                peer_query = await session.execute(select(Receiver).filter(Receiver.name.in_(peer_names)))
                peer_dict = {peer.name: peer for peer in peer_query.scalars().all()}
                peers = [peer_dict.get(name) for name in peer_names if
                         peer_dict.get(name) and peer_dict.get(name) not in ric.peers]
                if peers:
                    ric.peers.extend(peers)
        except Exception as e:
            print(client_readsb, clients_readsb)
            print(f"Receiver: {client_readsb[0]} not elaborated, error: {e}")

    # Processing
    for receiver_readsb in tqdm(receivers_readsb, desc="Adding CLIENTS to internal db"):
        matched_clients = [client for client in clients_readsb if receiver_readsb[0] == client[0][:18]]
        for client_readsb in matched_clients:
            await add_or_update_receiver(receiver_readsb, client_readsb)

    # Commit changes
    try:
        await session.commit()
    except Exception as e:
        print(f"Error occurred committing: {e}")
        await session.rollback()
