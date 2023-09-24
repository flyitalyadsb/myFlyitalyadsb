import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, Table, PickleType, Uuid, DateTime, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from utility.config import config

DATABASE_URL = config.url_db

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
Base = declarative_base()


async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Aircraft(Base):
    __tablename__ = "aircraft"
    id = Column(Integer, primary_key=True, autoincrement=True)
    icao = Column(String(7), nullable=False)
    registration = Column(String(20))
    icao_type_code = Column(String(3))
    type = Column(String(100))
    civ_mil = Column(Boolean)
    operator = Column(String(100))
    serial_number = Column(String(100))
    operator_icao = Column(String(3))

    def repr(self):
        repr = AircraftRep(self.id, self.icao, self.registration, self.icao_type_code, self.type, self.civ_mil,
                           self.operator)
        return repr


class AircraftRep:
    def __init__(self, id, icao, registration, icao_type_code, type, civ_mil, operator):
        self.id: int = id
        self.icao: str = icao
        self.registration: str = registration
        self.icao_type_code: str = icao_type_code
        self.type: str = type
        self.civ_mil: bool = civ_mil
        self.operator: str = operator


receiver_peers_association = Table('receiver_peers', Base.metadata,
                                   Column('receiver_id', Integer, ForeignKey('receiver.id'),
                                          primary_key=True),
                                   Column('peer_id', Integer, ForeignKey('receiver.id'),
                                          primary_key=True)
                                   )


class Receiver(Base):
    __tablename__ = "receiver"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(40))
    uuid = Column(String(36), unique=True, nullable=True)
    position_counter = Column(Float)
    timed_out_counter = Column(Float)
    lat_min = Column(Float)
    lat_max = Column(Float)
    lon_min = Column(Float)
    lon_max = Column(Float)
    lat_avg = Column(Float)
    lon_avg = Column(Float)
    lat = Column(Float)
    lon = Column(Float)
    alt = Column(Float)
    session_data = relationship('SessionData', back_populates='receiver')
    ip = Column(String(15))
    messagges_per_sec = Column(Integer)
    peers = relationship('Receiver',
                         secondary=receiver_peers_association,
                         primaryjoin=id == receiver_peers_association.c.receiver_id,
                         secondaryjoin=id == receiver_peers_association.c.peer_id,
                         backref='connected_to')


flights_receiver = Table('flights_receiver', Base.metadata,
                         Column('flight_id', Integer, ForeignKey('flight.id'), primary_key=True),
                         Column('receiver_id', Integer, ForeignKey('receiver.id'), primary_key=True)
                         )


class Flight(Base):
    __tablename__ = "flight"
    id = Column(Integer, primary_key=True, autoincrement=True)
    aircraft_id = Column(Integer, ForeignKey('aircraft.id'), nullable=False)
    aircraft = relationship('Aircraft', backref='flight')
    start = Column(DateTime)
    end = Column(DateTime)
    squawk = Column(String(4))
    ended = Column(Boolean())
    receiver = relationship('Receiver', secondary=flights_receiver, backref=backref('flight', lazy=True))


class FlightRep:
    def __init__(self, volo: Flight):
        self.id: int = volo.id
        self.icao: str = volo.aircraft.icao
        self.registration: str = volo.aircraft.registration
        self.operator: str = volo.aircraft.operator
        self.ICAOTypeCode = volo.aircraft.icao_type_code
        self.CivMil = volo.aircraft.civ_mil
        self.start: datetime.datetime = volo.start
        self.end: datetime.datetime = volo.end
        self.squawk: str = volo.squawk
        self.ended: bool = volo.ended

    def to_dict(self):
        return {
            "id": self.id,
            "icao": self.icao,
            "Registration": self.registration,
            "Operator": self.operator,
            "ICAOTypeCode": self.ICAOTypeCode,
            "CivMil": self.CivMil,
            "start": self.start,
            "end": self.end,
            "squawk": self.squawk,
            "ended": self.ended
        }


class SessionData(Base):
    __tablename__ = "session_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_uuid = Column(Uuid)
    message = Column(String(100))
    report = Column(JSON)
    uuid = Column(String(36), ForeignKey('receiver.uuid'))
    logged_in = Column(Boolean)
    logging = Column(Boolean)
    position = Column(Boolean)
    radius = Column(Integer)
    search = Column(String(50))
    selected_page = Column(Integer)
    filter = Column(String(50))
    sort = Column(String(10))
    only_mine = Column(Boolean)
    mode = Column(PickleType)
    receiver = relationship('Receiver', back_populates='session_data')
