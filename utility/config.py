from argparse import Namespace
from utility.parser import get_args


class Config:
    def __init__(self, args: Namespace) -> None:
        # server_main
        self.host: str = args.server_listen[0]
        if args.server_listen[1]:
            self.port: int = int(args.server_listen[1])
        self.debug: bool = args.debug
        self.deployment: bool = args.deployment
        self.deployment_host: str = args.deployment_host
        if args.deployment_port:
            self.deployment_port: int = int(args.deployment_port)

        # readsb_input
        self.aircraft_json: str = args.aircraft_json
        self.receiver_json: str = args.receivers_json
        self.clients_json: str = args.clients_json
        self.url_readsb: str = args.url_readsb

        # mlat_server_input
        self.sync_json: str = args.sync_json
        self.clients_mlat_json: str = args.clients_mlat_json

        # online_database_input
        self.db_open_dir = args.online_db_path

        self.url_open: str = args.url_online_db
        self.timeout: int | float = args.db_request_timeout

        # database_input
        self.url_db: str = args.url_db

        # unix
        self.unix: bool = args.unix
        self.unix_socket = args.unix_socket

        # web
        self.per_page: int = args.per_page

        self.aircraft_update = args.aircraft_update
        self.clients_and_db_update: int | float = args.clients_and_db_update  # time to wait until next sync_clients_and_db

        if self.deployment:
            self.aircraft_json = "/deployment/json/aircraft.json"
            self.receiver_json = "/deployment/json/ingest/receivers.json"
            self.clients_json = "/deployment/json/ingest/clients.json"
            self.sync_json = "/deployment/mlat/sync.json"
            self.clients_mlat_json = "/deployment/mlat/clients.json"
            self.db_open_dir = "/deployment/dati/"
            self.timeout = 10

        self.db_open_zip = self.db_open_dir + "open.zip"
        self.db_open = self.db_open_dir + "media/data/samples/metadata/aircraftDatabase.csv"


args_gotten = get_args()
config: Config = Config(args_gotten)
