from typing import Union, List, Optional, Any


class DatabaseDict:  # database opensky
    def __init__(self, row):
        self.registration = row['registration']
        self.manufacturericao = row['manufacturericao']
        self.manufacturername = row['manufacturername']
        self.model = row['model']
        self.typecode = row['typecode']
        self.serialnumber = row['serialnumber']
        self.linenumber = row['linenumber']
        self.icaoaircrafttype = row['icaoaircrafttype']
        self.operator = row['operator']
        self.operatorcallsign = row['operatorcallsign']
        self.operatoricao = row['operatoricao']
        self.operatoriata = row['operatoriata']
        self.owner = row['owner']
        self.testreg = row['testreg']
        self.registered = row['registered']
        self.reguntil = row['reguntil']
        self.status = row['status']
        self.built = row['built']
        self.firstflightdate = row['firstflightdate']
        self.seatconfiguration = row['seatconfiguration']
        self.engines = row['engines']
        self.modes = row['modes']
        self.adsb = row['adsb']
        self.acars = row['acars']
        self.notes = row['notes']
        self.categoryDescription = row['categoryDescription']


class AircraftDataRaw(dict):  # aircraft di aircrafts.json
    """
    This class represents individual aircraft data from '/json/aircrafts.json'.

    Attributes:
        hex: 24-bit ICAO identifier of the aircraft, possibly starting with '~' for non-ICAO addresses.
        type: Type of underlying messages, specifying the data source (e.g., adsb_icao, mlat, etc.)
        flight: Callsign, flight name or aircraft registration.
        alt_baro: Barometric altitude in feet or "ground".
        alt_geom: Geometric altitude in feet referenced to the WGS84 ellipsoid.
        gs: Ground speed in knots.
        ias: Indicated air speed in knots.
        tas: True air speed in knots.
        mach: Mach number.
        track: True track over ground in degrees (0-359).
        track_rate: Rate of change of track, in degrees/second.
        roll: Roll in degrees, negative indicates left roll.
        mag_heading: Heading in degrees, clockwise from magnetic north.
        true_heading: Heading in degrees, clockwise from true north.
        baro_rate: Rate of change of barometric altitude, in feet/minute.
        geom_rate: Rate of change of geometric altitude, in feet/minute.
        squawk: Mode A code, encoded as 4 octal digits.
        emergency: ADS-B emergency/priority status.
        category: Emitter category for aircraft or vehicle classes.
        nav_qnh: Altimeter setting, in hPa.
        nav_altitude_mcp: Selected altitude from the Mode Control Panel or equivalent.
        nav_altitude_fms: Selected altitude from the Flight Management System.
        nav_heading: Selected heading (usually magnetic).
        nav_modes: Engaged automation modes.
        lat, lon: Aircraft position in decimal degrees.
        nic: Navigation Integrity Category.
        rc: Radius of Containment, in meters.
        seen_pos: Time in seconds since the position was last updated.
        version: ADS-B Version Number.
        nic_baro: Navigation Integrity Category for Barometric Altitude.
        nac_p: Navigation Accuracy for Position.
        nac_v: Navigation Accuracy for Velocity.
        sil: Source Integrity Level.
        sil_type: Interpretation of SIL.
        gva: Geometric Vertical Accuracy.
        sda: System Design Assurance.
        mlat: Fields derived from MLAT data.
        tisb: Fields derived from TIS-B data.
        messages: Total number of Mode S messages received from this aircraft.
        seen: Time in seconds since a message was last received from this aircraft.
        rssi: Recent average RSSI (signal power) in dbFS.
        alert: Flight status alert bit.
        spi: Flight status special position identification bit.
        wd, ws: Wind direction and speed, derived from various parameters.
        oat, tat: Air temperatures, calculated from Mach number and true airspeed.
        acas_ra: Experimental attribute for ACAS.
        gpsOkBefore: Experimental attribute indicating past GPS status.
    """

    def __init__(self,
                 hex: str,
                 type: str,
                 flight: str,
                 alt_baro: Union[int, str],
                 alt_geom: int,
                 gs: int,
                 ias: int,
                 tas: int,
                 mach: float,
                 track: int,
                 track_rate: float,
                 roll: float,
                 mag_heading: float,
                 true_heading: float,
                 baro_rate: int,
                 geom_rate: int,
                 squawk: str,
                 emergency: str,
                 category: str,
                 nav_qnh: float,
                 nav_altitude_mcp: int,
                 nav_altitude_fms: int,
                 nav_heading: float,
                 nav_modes: List[str],
                 lat: float,
                 lon: float,
                 nic: int,
                 rc: int,
                 seen_pos: int,
                 version: int,
                 nic_baro: int,
                 nac_p: int,
                 nac_v: int,
                 sil: int,
                 sil_type: str,
                 gva: int,
                 sda: int,
                 mlat: List[str],
                 tisb: List[str],
                 messages: int,
                 seen: int,
                 rssi: float,
                 alert: int,
                 spi: int,
                 wd: Optional[int],
                 ws: Optional[int],
                 oat: Optional[float],
                 tat: Optional[float],
                 acas_ra: Any,
                 gpsOkBefore: Any,
                 ReceiversUuids: str):
        super().__init__()
        self["hex"] = hex
        self["type"] = type
        self["flight"] = flight
        self["alt_baro"] = alt_baro
        self["alt_geom"] = alt_geom
        self["gs"] = gs
        self["ias"] = ias
        self["tas"] = tas
        self["mach"] = mach
        self["track"] = track
        self["track_rate"] = track_rate
        self["roll"] = roll
        self["mag_heading"] = mag_heading
        self["true_heading"] = true_heading
        self["baro_rate"] = baro_rate
        self["geom_rate"] = geom_rate
        self["squawk"] = squawk
        self["emergency"] = emergency
        self["category"] = category
        self["nav_qnh"] = nav_qnh
        self["nav_altitude_mcp"] = nav_altitude_mcp
        self["nav_altitude_fms"] = nav_altitude_fms
        self["nav_heading"] = nav_heading
        self["nav_modes"] = nav_modes
        self["lat"] = lat
        self["lon"] = lon
        self["nic"] = nic
        self["rc"] = rc
        self["seen_pos"] = seen_pos
        self["version"] = version
        self["nic_baro"] = nic_baro
        self["nac_p"] = nac_p
        self["nac_v"] = nac_v
        self["sil"] = sil
        self["sil_type"] = sil_type
        self["gva"] = gva
        self["sda"] = sda
        self["mlat"] = mlat
        self["tisb"] = tisb
        self["messages"] = messages
        self["seen"] = seen
        self["rssi"] = rssi
        self["alert"] = alert
        self["spi"] = spi
        self["wd"] = wd
        self["ws"] = ws
        self["oat"] = oat
        self["tat"] = tat
        self["acas_ra"] = acas_ra
        self["gpsOkBefore"] = gpsOkBefore
        self["ReceiversUuids"] = ReceiversUuids


class AircraftsJson:
    """
    This class represents the structure of '/json/aircrafts.json'.

    Attributes:
        - now: The current timestamp.
        - messages: The number of messages.
        - aircraft: A list containing data for each individual aircraft.
    """
    now: int
    messages: int
    aircraft: List[AircraftDataRaw]

class info:
    id: int
    icao: str
    Registration: str
    ICAOTypeCode: str
    Type: str
    CivMil: bool
    Operator: str

class AircraftsJsonDaServire:
    """
    This class represents the structure of '/json/aircrafts.json modified by adding info from opensky db'.

    Attributes:
        - now: The current timestamp.
        - messages: The number of messages.
        - aircraft: A list containing data for each individual aircraft.
        - info: an instance of DbDizionario
    """
    now: int
    messages: int
    aircraft: List[AircraftDataRaw]
    info: info



class Receiver:
    """
    This class represents individual receiver data from '/json/receivers.json'.

        Attributes:
        - uuid: The uuid of the receiver.
        - position_counter: The number of positions received / elapsed time
        - timed_out_counter:
        - lat_min:
        - lat_max:
        - lon_min:
        - lon_max:
        - bad_extent:
        - lat_avg: latMin + (latMax - latMin) / 2.0
        - lon_avg: lonMin + (lonMax - lonMin) / 2.0
    """

    uuid: str
    position_counter: float
    timed_out_counter: float
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    bad_extent: bool
    lat_avg: float
    lon_avg: float


class ReceiversJson:
    """
    This class represents the structure of '/json/receivers.json'.

    Attributes:
        - now: The current timestamp.
        - receivers: A list containing data for each individual receiver.
    """
    now: float
    receivers: List[Receiver]


class Client:
    uuid: str
    host_port: str
    avg_kbps: float
    connection_time: float
    messages_per_second: float
    positions_per_second: float
    reduce_signaled: bool
    recent_rtt: float
    position_counter: int


class ClientsJson:
    """
    This class represents the structure of '/json/clients.json'.

    Attributes:
        - now: The current timestamp.
        - format: The format of clients fields
        - clients: A list containing data for each individual client.
    """
    now: float
    format: List[str]
    clients: List[Client]
