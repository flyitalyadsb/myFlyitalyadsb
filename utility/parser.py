import argparse


def host_and_ports(string):
    try:
        parts = string.split(':')
        if len(parts) != 2:
            raise ValueError()
        return parts[0], int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{string} should be in this formats: 'host:tcp_port'")


def list_of_strings(arg):
    return arg.split(',')


def server_main(parser):
    parser.add_argument('--server-listen',
                        help="Specify the address and port for the server to listen on (format: 'host:port').",
                        type=host_and_ports,
                        default="0.0.0.0:83")
    parser.add_argument('--debug',
                        help="enter in debug mode",
                        action='store_true',
                        default=False
                        )
    parser.add_argument('--only-asyncio-debug',
                        help="set asyncio in debug mode",
                        action='store_true',
                        default=False
                        )


def readsb_input(parser):
    parser.add_argument('--aircraft-json',
                        help="Path to the aircraft JSON data file.",
                        default="/json/aircraft.json")

    parser.add_argument('--receivers-json',
                        help="Path to the receivers JSON data file.",
                        default="/json/ingest/receivers.json")

    parser.add_argument('--clients-json',
                        help="Path to the clients JSON data file.",
                        default="/json/ingest/clients.json")

    parser.add_argument('--url-readsb',
                        help="URL to readsb service.",
                        default="https://mappa.flyitalyadsb.com/re-api/?all")

    parser.add_argument('--readsb-request-timeout',
                        type=int,
                        help="Timeout duration for readsb requests (in seconds).",
                        default=3)


def mlat_server_input(parser):
    parser.add_argument('--sync-json',
                        help="Path to the synchronization JSON data file.",
                        default="/mlat/sync.json")

    parser.add_argument('--clients-mlat-json',
                        help="Path to the mlat clients JSON data file.",
                        default="/mlat/clients.json")


def online_database_input(parser):
    parser.add_argument('--online-db-path',
                        help="Local path for the online database storage.",
                        default="./dati")

    parser.add_argument('--url-online-db',
                        help="URL to fetch the online aircraft database.",
                        default="https://opensky-network.org/datasets/metadata/aircraftDatabase.zip")


def database_input(parser):
    parser.add_argument('--url-db',
                        help="Database connection URL.",
                        default="sqlite+aiosqlite:////database/db.sqlite")


def unix_input(parser):
    parser.add_argument('--unix',
                        help="Flag to use Unix instead of HTTP for connecting to the readsb API.",
                        action='store_true',
                        default=False
                        )
    parser.add_argument('--unix-socket',
                        help="Path to the Unix socket for readsb API.",
                        default="/json/api.sock")


def web(parser):
    parser.add_argument('--per-page',
                        help="Specify the number of results displayed per page.",
                        default=50)


def frequencies(parser):
    parser.add_argument('--aircraft-update',
                        help="Set the frequency of aircraft updates (in seconds).",
                        default=0.5)
    parser.add_argument('--clients-and-db-update',
                        help="Set the frequency of clients and database updates (in seconds).",
                        default=3)


def web_admin(parser):
    parser.add_argument('--editors',
                        type=list_of_strings,
                        help="The names of receivers able to edit aircraft-db and access to /editor.",
                        )


def get_parser():
    parser = argparse.ArgumentParser(description="MyFlyitalyadsb")
    server_main(parser.add_argument_group("Main options"))
    readsb_input(parser.add_argument_group('Readsb options'))
    mlat_server_input(parser.add_argument_group('Mlat server options'))
    online_database_input(parser.add_argument_group('Online database options'))
    database_input(parser.add_argument_group('Database options'))
    web_admin(parser.add_argument_group("Web-admin options"))
    unix_input(parser.add_argument_group('Unix options'))
    web(parser.add_argument_group('Web options'))
    frequencies(parser.add_argument_group("Update frequencies options"))
    return parser


def get_args():
    parser = get_parser()
    args = parser.parse_args()
    return args
