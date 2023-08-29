from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, Table, PickleType, Uuid, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from pydantic import BaseModel

DATABASE_URL = "sqlite+aiosqlite:///tempo_reale3.sqlite"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
Base = declarative_base()
# isolation_level = "READ UNCOMMITTED"


class Aereo(Base):
    __tablename__ = "aereo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    icao = Column(String(20), nullable=False)
    Registration = Column(String(100))
    ICAOTypeCode = Column(String(20))
    Type = Column(String(100))
    CivMil = Column(Boolean)
    Operator = Column(String(80))
    SerialNumber = Column(String(80))
    OperatorIcao = Column(String(80))

    def repr(self):
        repr = Aereo_rep(self.id, self.icao, self.Registration, self.ICAOTypeCode, self.Type, self.CivMil,
                         self.Operator)
        return repr


class Aereo_rep():
    def __init__(self, id, icao, Registration, ICAOTypeCode, Type, CivMil, Operator):
        self.id: int = id
        self.icao: str = icao
        self.Registration: str = Registration
        self.ICAOTypeCode: str = ICAOTypeCode
        self.Type: str = Type
        self.CivMil: bool = CivMil
        self.Operator: str = Operator


ricevitore_peers_association = Table('ricevitore_peers', Base.metadata,
                                     Column('ricevitore_id', Integer, ForeignKey('ricevitore.id'),
                                            primary_key=True),
                                     Column('peer_id', Integer, ForeignKey('ricevitore.id'),
                                            primary_key=True)
                                     )


class Ricevitore(Base):
    __tablename__ = "ricevitore"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(40))
    uuid = Column(String(22), unique=True, nullable=True)
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
    linked = Column(Boolean, default=False)
    session_data = relationship('SessionData', back_populates='ricevitore')
    ip = Column(String(40))
    messaggi_al_sec = Column(Integer)
    peers = relationship('Ricevitore',
                         secondary=ricevitore_peers_association,
                         primaryjoin=id == ricevitore_peers_association.c.ricevitore_id,
                         secondaryjoin=id == ricevitore_peers_association.c.peer_id,
                         backref='connected_to')


class Volo(Base):
    __tablename__ = "volo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    aereo_id = Column(Integer, ForeignKey('aereo.id'), nullable=False)
    aereo = relationship('Aereo', backref='voli')
    inizio = Column(String(40))
    fine = Column(String(40))
    squawk = Column(String(40))
    traccia_conclusa = Column(Boolean())


ricevitori_voli = Table('ricevitori_voli', Base.metadata,
                        Column('volo_id', Integer, ForeignKey('volo.id'), primary_key=True),
                        Column('ricevitore_id', Integer, ForeignKey('ricevitore.id'), primary_key=True)
                        )
Volo.ricevitore = relationship('Ricevitore', secondary=ricevitori_voli, backref=backref('voli', lazy=True))


class Volo_rep():
    def __init__(self, volo: "Volo"):
        self.id: int = volo.id
        self.icao: str = volo.aereo.icao
        self.registrazione: str = volo.aereo.Registration
        self.operator: str = volo.aereo.Operator
        self.ICAOTypeCode = volo.aereo.ICAOTypeCode
        self.CivMil = volo.aereo.CivMil
        self.inizio: int = volo.inizio
        self.fine: int = volo.fine
        self.squawk: str = volo.squawk
        self.traccia_conclusa: bool = volo.traccia_conclusa

    def to_dict(self):
        return {
            "id": self.id,
            "icao": self.icao,
            "Registration": self.registrazione,
            "Operator": self.operator,
            "ICAOTypeCode": self.ICAOTypeCode,
            "CivMil": self.CivMil,
            "inizio": self.inizio,
            "fine": self.fine,
            "squawk": self.squawk,
            "traccia_conclusa": self.traccia_conclusa
        }


class SessionData(Base):
    __tablename__ = "session_data"
    id = Column(Integer, primary_key=True, autoincrement=True)  # Usiamo l'ID della sessione come chiave primaria
    session_uuid = Column(Uuid)
    data = Column(PickleType)  # Memorizziamo i dati della sessione serializzati
    ricevitore_uuid = Column(Integer, ForeignKey('ricevitore.uuid'))
    logged_in = Column(Boolean)
    posizione = Column(Boolean)
    selected_page = Column(Integer)
    filter = Column(String)
    sort = Column(String)
    only_mine = Column(Boolean)
    modalita = Column(PickleType)
    ricevitore = relationship('Ricevitore', back_populates='session_data')


class RicevitorePydantic(BaseModel):
    id: int
    name: str
    uuid: str
    position_counter: float
    timed_out_counter: float
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    lat_avg: float
    lon_avg: float
    lat: float
    lon: float
    linked: bool
    ip: str
    messaggi_al_sec: int
class SessionDataPydantic(BaseModel):
    id: int
    session_uuid: str
    ricevitore_uuid: int
    logged_in: bool
    posizione: bool
    selected_page: int
    filter: str
    sort: str
    only_mine: bool
    modalita: dict
    ricevitore: RicevitorePydantic


