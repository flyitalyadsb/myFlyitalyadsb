import datetime
import gzip
import json
import os

dir = 'F:/globe_history_prova/'


@app_context
def getINFO_or_add_aircraft(database_open, icao: str, icao_presenti_nel_db):
    if not icao.upper() in icao_presenti_nel_db:
        app.logger.debug(f"{icao} non presente nel database")
        link = "https://mappa.flyitalyadsb.com/?icao=" + icao
        if icao.upper() in database_open.keys():  # icao presente nel db di tar1090
            db_data = database_open[icao.upper()]
            logging.debug(f"Aggiungo {icao} nel database interno")
            reg = db_data["registration"]
            type = db_data["icaoaircrafttype"]
            model = db_data["model"]
            db.session.add(Aerei(icao=icao.upper(), Registration=reg, ICAOTypeCode=type, Type=model, link=link))
            db.session.commit()
            info = Aerei.query.all()[-1]
            aircraft_cache[icao] = info

        else:
            db.session.add(Aerei(icao=icao.upper(), link=link))
            db.session.commit()
            info = Aerei.query.all()[-1]
            aircraft_cache[icao] = info
    else:
        logging.debug(f"{icao} presente nel nostro database, restituiamo le info che conosciamo")
        info = Aerei.query.filter_by(icao=icao.upper()).first()
        aircraft_cache[icao] = info
    return info


@app_context
def convert_globe_to_db():
    for year in os.scandir(dir):
        for month in os.scandir(year.path):
            for day in os.scandir(month.path):
                for subclasses in os.scandir(day.path):
                    for file in os.scandir(subclasses.path):
                        with gzip.open(file, 'rb') as json_file:
                            try:
                                data = json.load(json_file)
                            except:
                                pass
                        icao = data["icao"]
                        timeZero = data['timestamp']
                        trace = data['trace']
                        ftime = datetime.datetime.fromtimestamp(timeZero)
                        ltime = datetime.datetime.fromtimestamp(timeZero + trace[-1][0])

                        if isinstance(trace[0][8], dict):
                            fkeys = trace[0][8].keys()
                        else:
                            fkeys = []
                        if isinstance(trace[-1][8], dict):
                            lkeys = trace[-1][8].keys()
                        else:
                            lkeys = []

                        if "squawk" in fkeys:
                            squawk = trace[0][8]["squawk"]
                        elif "squawk" in lkeys:
                            squawk = trace[-1][8]["squawk"]
                        else:
                            squawk = ""
                        if "flight" in fkeys:
                            cl = trace[0][8]["flight"]
                        elif "flight" in lkeys:
                            cl = trace[-1][8]["flight"]
                        else:
                            cl = ""
                        info = getINFO_or_add_aircraft(database_open, icao)
                        if info.link:
                            link_report = info.link + "&showTrace=" + ftime.strftime("%Y-%m-%d")
                        else:
                            link_report = ""
                        db.session.add(
                            Voli(aereo_id=info.id, squawk=squawk, inizio=ftime.timestamp(), fine=ltime.timestamp(),
                                 link_report=link_report, traccia_conclusa=True))
                        db.session.commit()


def app_context(f):
    if asyncio.iscoroutinefunction(f):
        async def decorated(*args, **kwargs):
            with app.app_context():
                with db.session.no_autoflush:
                    return await f(*args, **kwargs)
    else:
        def decorated(*args, **kwargs):
            with app.app_context():
                with db.session.no_autoflush:
                    return f(*args, **kwargs)

    return decorated


@app_context
def get_aircrafts(db_tar, data):
    global icao_presenti_nel_db
    aircrafts = data["aircraft"]
    for aircraft in aircrafts:
        if aircraft["hex"] not in aircraft_cache:
            info = getINFO_or_add_aircraft(database_open, aircraft["hex"], icao_presenti_nel_db)
        else:
            info = aircraft_cache[aircraft["hex"]]
        aircraft["info"] = info
        aircraft["edit"] = "https://listavoli.flyitalyadsb.com/editor?icao=" + aircraft["hex"]

    return aircrafts
