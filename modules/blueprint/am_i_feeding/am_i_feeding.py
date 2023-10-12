import asyncio
import datetime

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from modules.blueprint.commonMy.commonMy import check_ip, proxy_ip
from modules.clients.clients import convert_to_ip, read_file
from utility.config import config
from utility.model import Receiver

amIFeeding_bp = APIRouter()


async def am_i_feeding_real(request: Request):
    session_db: AsyncSession = request.state.session_db
    receiver: Receiver = await check_ip(request, session_db)
    beast = False
    mlat = False
    if receiver and datetime.datetime.now() - receiver.last_seen < datetime.timedelta(seconds=180):
        beast = True
        if receiver.lat:
            mlat = True

    return beast, mlat


async def am_i_feeding_debug(request: Request):
    beast = False
    mlat = False
    request_ip = proxy_ip(request)

    clients_readsb, clients_mlat = await asyncio.gather(read_file(config.clients_json), read_file(config.clients_mlat_json))
    for client in clients_readsb:
        if convert_to_ip(client[1]) == request_ip:
            beast = True
            client_mlat_data = next(
                (c for c in clients_mlat.values() if c["uuid"] and (c["uuid"] == client[0] or client[0] in c["uuid"])),
                None)
            if client_mlat_data:
                mlat = True

    return beast, mlat


@amIFeeding_bp.api_route('/am_i_feeding', methods=["GET"])
async def am_i_feeding(request: Request):
    beast, mlat = await am_i_feeding_debug(request)
    return {"feeding": {"beast": beast, "mlat": mlat}}
