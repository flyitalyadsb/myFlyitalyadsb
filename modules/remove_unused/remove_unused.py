import asyncio
import datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from utility.model import SessionLocal, SessionData, Receiver


async def remove_unused():
    session_db: AsyncSession = SessionLocal()
    time_threshold = datetime.datetime.now() - datetime.timedelta(days=10)
    await session_db.execute(
        delete(SessionData).filter(SessionData.last_seen < time_threshold)
    )
    await session_db.execute(
        delete(Receiver).filter(Receiver.last_seen < time_threshold)
    )
    await asyncio.sleep(60 * 60 * 24 * 1)  # once a day
