from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from modules.blueprint.commonMy.commonMy import check_ip
from utility.model import Receiver

amIFeeding_bp = APIRouter()


@amIFeeding_bp.api_route('/login', methods=["GET", "POST"])
async def am_i_feeding(request: Request):
    session_db: AsyncSession = request.state.session_db
    receiver: Receiver = await check_ip(request, session_db)
    beast = False
    mlat = False
    if receiver:
        beast = True
        if receiver.lat:
            mlat = True
    return {"feeding": {"beast": beast, "mlat": mlat}}
