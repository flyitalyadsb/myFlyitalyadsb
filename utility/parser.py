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


def server_main(parser):
    parser.add_argument('--server-listen',
                        help="listen on a host:tcp_port",
                        type=host_and_ports,
                        default="0.0.0.0:83"
                        )
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
                        help="write results in CSV format to a local file.",
                        default="/json/aircraft.json")

    parser.add_argument('--receivers-json',
                        help="write results in CSV format to a local file.",
                        default="/json/ingest/receivers.json")

    parser.add_argument('--clients-json',
                        help="write results in CSV format to a local file.",
                        default="/json/ingest/clients.json")

    parser.add_argument('--url-readsb',
                        help="Url to readsb. example: readsb:30152 if you have your readsb with --net-tar1090-api 20152"
                             "in a docker container named readsb",
                            default="https://mappa.flyitalyadsb.com/re-api/?all")
    parser.add_argument('--readsb-request-timeout',
                        help="write results in CSV format to a local file.",
                        default=3)


def mlat_server_input(parser):
    parser.add_argument('--sync-json',
                        help="write results in CSV format to a local file.",
                        default="/mlat/sync.json")

    parser.add_argument('--clients-mlat-json',
                        help="write results in CSV format to a local file.",
                        default="/mlat/clients.json")


def online_database_input(parser):
    parser.add_argument('--online-db-path',
                        help="write results in CSV format to a local file.",
                        default="/dati")
    parser.add_argument('--url-online-db',
                        help="write results in CSV format to a local file.",
                        default="https://opensky-network.org/datasets/metadata/aircraftDatabase.zip")



def database_input(parser):
    parser.add_argument('--url-db',
                        help="write results in CSV format to a local file.",
                        default="sqlite+aiosqlite:////database/db.sqlite")


def unix_input(parser):
    parser.add_argument('--unix',
                        help="Use unix instead http to connect to readsb api",
                        action='store_true',
                        default=False
                        )
    parser.add_argument('--unix_socket',
                        help="Path to unix socket, default: unix:/run/readsb/api.sock",
                        default="unix:/run/readsb/api.sock")


def web(parser):
    parser.add_argument('--per-page',
                        help="write results in CSV format to a local file.",
                        default=50)


def frequencies(parser):
    parser.add_argument('--aircraft-update',
                        help="write results in CSV format to a local file.",
                        default=0.2)
    parser.add_argument('--clients-and-db-update',
                        help="write results in CSV format to a local file.",
                        default=3)


def get_parser():
    parser = argparse.ArgumentParser(description="MyFlyitalyadsb")
    server_main(parser.add_argument_group("Main options"))
    readsb_input(parser.add_argument_group('Readsb options'))
    mlat_server_input(parser.add_argument_group('Mlat server options'))
    online_database_input(parser.add_argument_group('Online database options'))
    database_input(parser.add_argument_group('Database options'))

    unix_input(parser.add_argument_group('Unix options'))
    web(parser.add_argument_group('Web options'))
    frequencies(parser.add_argument_group("Update frequencies options"))
    return parser


def get_args():
    parser = get_parser()
    args = parser.parse_args()
    return args
