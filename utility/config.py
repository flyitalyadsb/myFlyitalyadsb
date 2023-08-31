import os
import platform
SECRET_KEY = os.urandom(32)


FIRST_TIME = False

debug = False

#path
AIRCRAFT_JSON = "/json/aircraft.json"
RECEIVERS_JSON = "/json/ingest/receivers.json"
CLIENTS_JSON = "/json/ingest/clients.json"

SYNC_JSON = "/mlat/sync.json"
CLIENTS_MLAT_JSON = "/mlat/clients.json"
DB_OPEN_DIR = "../dati/"
DB_OPEN_ZIP = "/dati/open.zip"
TIMEOUT = 3
FREQUENZA_AGGIORNAMENTO_AEREI = 0.2

if platform.system() == "Windows":
    AIRCRAFT_JSON = "./windows/json/aircraft.json"
    RECEIVERS_JSON = "./windows/json/ingest/receivers.json"
    CLIENTS_JSON = "./windows/json/ingest/clients.json"
    SYNC_JSON = "./windows/mlat/sync.json"
    CLIENTS_MLAT_JSON = "./windows/mlat/clients.json"
    DB_OPEN_ZIP = "./windows/dati/open.zip"
    DB_OPEN_DIR = "../windows/dati/"
    TIMEOUT = 10

URL_OPEN = "https://opensky-network.org/datasets/metadata/aircraftDatabase.zip"
DB_OPEN = DB_OPEN_DIR + "media/data/samples/metadata/aircraftDatabase.csv"

UPDATE_TOTAL = 0.5
URL_READSB = "https://mappa.flyitalyadsb.com/re-api/?all"

PER_PAGE = 50
UNIX = False
UNIX_SOCKET = "unix:/run/readsb/api.sock"

UPDATE_CLIENTS = 10 #seconds