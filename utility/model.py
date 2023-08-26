from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(engine_options={"pool_size": 40})


class Aereo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    icao = db.Column(db.String(20), nullable=False)
    Registration = db.Column(db.String(100))
    ICAOTypeCode = db.Column(db.String(20))
    Type = db.Column(db.String(100))
    CivMil = db.Column(db.Boolean)
    Operator = db.Column(db.String(80))
    SerialNumber = db.Column(db.String(80))
    OperatorIcao = db.Column(db.String(80))

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


ricevitori_voli = db.Table('ricevitori_voli',
                           db.Column('volo_id', db.Integer, db.ForeignKey('volo.id'), primary_key=True),
                           db.Column('ricevitore_id', db.Integer, db.ForeignKey('ricevitore.id'), primary_key=True)
                           )


class Volo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aereo_id = db.Column(db.Integer, db.ForeignKey('aereo.id'), nullable=False)
    aereo = db.relationship('Aereo', backref='voli')
    inizio = db.Column(db.String(40))
    fine = db.Column(db.String(40))
    squawk = db.Column(db.String(40))
    traccia_conclusa = db.Column(db.Boolean())
    ricevitori = db.relationship('Ricevitore', secondary=ricevitori_voli, backref=db.backref('voli', lazy=True))


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


ricevitore_peers_association = db.Table('ricevitore_peers',
                                        db.Column('ricevitore_id', db.Integer, db.ForeignKey('ricevitore.id'),
                                                  primary_key=True),
                                        db.Column('peer_id', db.Integer, db.ForeignKey('ricevitore.id'),
                                                  primary_key=True)
                                        )


class Ricevitore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    uuid = db.Column(db.String(22), unique=True, nullable=True)
    position_counter = db.Column(db.Float)
    timed_out_counter = db.Column(db.Float)
    lat_min = db.Column(db.Float)
    lat_max = db.Column(db.Float)
    lon_min = db.Column(db.Float)
    lon_max = db.Column(db.Float)
    lat_avg = db.Column(db.Float)
    lon_avg = db.Column(db.Float)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    linked = db.Column(db.Boolean, default=False)  # è collegato a mlat-server
    session_data = db.relationship('SessionData', back_populates='ricevitore')
    ip = db.Column(db.String(40))
    messaggi_al_sec = db.Column(db.Integer)
    peers = db.relationship('Ricevitore',
                            secondary=ricevitore_peers_association,
                            primaryjoin=id == ricevitore_peers_association.c.ricevitore_id,
                            secondaryjoin=id == ricevitore_peers_association.c.peer_id,
                            backref='connected_to')


class SessionData(db.Model):
    id = db.Column(db.String, primary_key=True)  # Usiamo l'ID della sessione come chiave primaria
    data = db.Column(db.PickleType)  # Memorizziamo i dati della sessione serializzati
    ricevitore_uuid = db.Column(db.Integer, db.ForeignKey('ricevitore.uuid'))
    ricevitore = db.relationship('Ricevitore', back_populates='session_data')
