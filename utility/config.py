import platform
from argparse import Namespace
from parser import get_args


class Config:
    def __init__(self, args: Namespace) -> None:

        # server_main
        self.host: str = args.server_listen.split(":")[0]
        self.port: int = args.server_listen.split(":")[1]
        self.debug: bool = args.debug
        self.deployment: bool = args.deployment
        self.deployment_host: str = args.deployment_host
        self.deployment_port: int = args.deployment_port

        # readsb_input
        self.aircraft_json: str = args.aircraft_json
        self.receiver_json: str = args.receiver_json
        self.clients_json: str = args.clients_json
        self.url_readsb: str = args.url_readsb

        # mlat_server_input
        self.sync_json: str = args.sync_json
        self.clients_mlat_json: str = args.clients_mlat_json

        # database_input
        self.url_open: str = args.url_onbline_db
        self.timeout: int | float = args.db_request_timeout

        self.db_open_dir = args.db_open_dir
        self.db_open_zip = self.db_open_dir + "/open.zip"

        self.db_open = self.db_open_dir + "media/data/samples/metadata/aircraftDatabase.csv"

        # unix
        self.unix: bool = args.unix
        self.unix_socket = args.unix_socket

        # web
        self.per_page: int = args.per_page

        self.aircraft_update = args.aircraft_update
        self.clients_and_db_update: int | float = args.clients_and_db_update  # time to wait until next sync_clients_and_db

        if self.deployment:
            self.aircraft_json = "./windows/json/aircraft.json"
            self.receiver_json = "./windows/json/ingest/receivers.json"
            self.clients_json = "./windows/json/ingest/clients.json"
            self.sync_json = "./windows/mlat/sync.json"
            self.clients_mlat_json = "./windows/mlat/clients.json"
            self.db_open_zip = "./windows/dati/open.zip"
            self.db_open_dir = "../windows/dati/"
            self.timeout = 10


args_gotten = get_args()
config: Config = Config(args_gotten)
