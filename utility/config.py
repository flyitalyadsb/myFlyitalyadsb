from argparse import Namespace
from utility.parser import get_args


class Config:
    def __init__(self, args: Namespace) -> None:
        # server_main
        self.host: str = args.server_listen[0]
        if args.server_listen[1]:
            self.port: int = int(args.server_listen[1])
        self.debug: bool = args.debug
        self.asyncio_debug = args.only_asyncio_debug

        # readsb_input
        self.aircraft_json: str = args.aircraft_json
        self.receiver_json: str = args.receivers_json
        self.clients_json: str = args.clients_json
        self.url_readsb: str = args.url_readsb
        self.timeout: int | float = float(args.readsb_request_timeout)

        # mlat_server_input
        self.sync_json: str = args.sync_json
        self.clients_mlat_json: str = args.clients_mlat_json

        # online_database_input
        self.db_open_dir: str = args.online_db_path
        if not self.db_open_dir.endswith("/"):
            self.db_open_dir = self.db_open_dir + "/"
        self.db_open_zip = self.db_open_dir + "open.zip"
        self.db_open = self.db_open_dir + "media/data/samples/metadata/aircraftDatabase.csv"
        self.url_open: str = args.url_online_db

        # database_input
        self.url_db: str = args.url_db

        # unix
        self.unix: bool = bool(args.unix)
        self.unix_socket = args.unix_socket

        # web
        self.per_page: int = int(args.per_page)

        self.aircraft_update = float(args.aircraft_update)
        self.clients_and_db_update: int | float = float(args.clients_and_db_update)  # time to wait until next
        # sync_clients_and_db


args_gotten = get_args()
config: Config = Config(args_gotten)
