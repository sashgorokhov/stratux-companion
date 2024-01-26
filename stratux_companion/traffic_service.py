import datetime
import json
import logging
from collections import OrderedDict
from threading import Lock
from typing import NamedTuple, List, Dict

from geopy.units import meters
from websockets import ConnectionClosed
from websockets.sync.client import connect

from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.util import GPS, ServiceWorker, km_h

"""
{"Icao_addr":11030261,"Reg":"N6340E","Tail":"N6340E","Emitter_category":1,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-28.873949984654253,"SignalLevelHist":null,"Squawk":3655,"Position_valid":true,"Lat":30.346046,"Lng":-97.770645,"Alt":4300,"GnssDiffFromBaroAlt":75,"AltIsGNSS":false,"NIC":8,"NACp":9,"Track":198,"TurnRate":0,"Speed":99,"Speed_valid":true,"Vvel":0,"Timestamp":"2024-01-12T05:30:20.777200261Z","PriorityStatus":0,"Age":59.72,"AgeLastAlt":59.72,"Last_seen":"0001-01-01T00:20:29.26Z","Last_alt":"0001-01-01T00:20:29.26Z","Last_GnssDiff":"0001-01-01T00:20:29.26Z","Last_GnssDiffAlt":4300,"Last_speed":"0001-01-01T00:20:29.26Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T00:21:28.75Z","AgeExtrapolation":0.23,"Lat_fix":30.372026,"Lng_fix":-97.76068,"Alt_fix":4300,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":261,"IsStratux":false}
{"Icao_addr":5883938,"Reg":"","Tail":"","Emitter_category":0,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-37.72113295386327,"SignalLevelHist":null,"Squawk":0,"Position_valid":true,"Lat":34.019497,"Lng":100.82681,"Alt":116957,"GnssDiffFromBaroAlt":0,"AltIsGNSS":true,"NIC":10,"NACp":0,"Track":149,"TurnRate":0,"Speed":4269,"Speed_valid":true,"Vvel":19520,"Timestamp":"2024-01-12T06:02:23.097187757Z","PriorityStatus":0,"Age":59.4,"AgeLastAlt":59.4,"Last_seen":"0001-01-01T00:52:31.58Z","Last_alt":"0001-01-01T00:52:31.58Z","Last_GnssDiff":"0001-01-01T00:00:00Z","Last_GnssDiffAlt":0,"Last_speed":"0001-01-01T00:52:31.58Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T00:53:30.91Z","AgeExtrapolation":0.07,"Lat_fix":35.024628,"Lng_fix":100.09388,"Alt_fix":97675,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":1,"IsStratux":false}
{"Icao_addr":11030261,"Reg":"N6340E","Tail":"N6340E","Emitter_category":1,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-27.95880017344075,"SignalLevelHist":null,"Squawk":2557,"Position_valid":true,"Lat":30.540617,"Lng":-97.71647,"Alt":5400,"GnssDiffFromBaroAlt":25,"AltIsGNSS":false,"NIC":8,"NACp":9,"Track":30,"TurnRate":0,"Speed":106,"Speed_valid":true,"Vvel":0,"Timestamp":"2024-01-12T07:10:34.301879322Z","PriorityStatus":0,"Age":4.2,"AgeLastAlt":4.2,"Last_seen":"0001-01-01T02:00:42.73Z","Last_alt":"0001-01-01T02:00:42.73Z","Last_GnssDiff":"0001-01-01T02:00:33.91Z","Last_GnssDiffAlt":5400,"Last_speed":"0001-01-01T02:00:42.73Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T02:00:46.36Z","AgeExtrapolation":0.57,"Lat_fix":30.539074,"Lng_fix":-97.7175,"Alt_fix":5400,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":55,"IsStratux":false}
"""

# Stratux /traffic endpoint message structure
# type TrafficInfo struct {
# 	Icao_addr           uint32
# 	Reg                 string    // Registration. Calculated from Icao_addr for civil aircraft of US registry.
# 	Tail                string    // Callsign. Transmitted by aircraft.
# 	Emitter_category    uint8     // Formatted using GDL90 standard, e.g. in a Mode ES report, A7 becomes 0x07, B0 becomes 0x08, etc.
# 	SurfaceVehicleType	uint16    // Type of service vehicle (when Emitter_category==18) 0..255 is reserved for AIS vessels
# 	OnGround            bool      // Air-ground status. On-ground is "true".
# 	Addr_type           uint8     // UAT address qualifier. Used by GDL90 format, so translations for ES TIS-B/ADS-R are needed.
# 	TargetType          uint8     // types decribed in const above
# 	SignalLevel         float64   // Signal level, dB RSSI.
# 	SignalLevelHist     []float64 // last 8 values. For 1090ES we store the last 8 values here. SignalLevel will then become the minimum of these to get more stable data with antenna diversity
# 	Squawk              int       // Squawk code
# 	Position_valid      bool      // set when position report received. Unset after n seconds?
# 	Lat                 float32   // decimal common.Degrees, north positive
# 	Lng                 float32   // decimal common.Degrees, east positive
# 	Alt                 int32     // Pressure altitude, feet
# 	GnssDiffFromBaroAlt int32     // GNSS altitude above WGS84 datum. Reported in TC 20-22 messages
# 	AltIsGNSS           bool      // Pressure alt = 0; GNSS alt = 1
# 	NIC                 int       // Navigation Integrity Category.
# 	NACp                int       // Navigation Accuracy Category for Position.
# 	Track               float32   // common.Degrees true
# 	TurnRate            float32   // Turn rate in deg/sec (negative = turning left, positive = right)
# 	Speed               uint16    // knots
# 	Speed_valid         bool      // set when speed report received.
# 	Vvel                int16     // feet per minute
# 	Timestamp           time.Time // timestamp of traffic message, UTC
# 	PriorityStatus      uint8     // Emergency or priority code as defined in GDL90 spec, DO-260B (Type 28 msg) and DO-282B
#
# 	// Parameters starting at 'Age' are calculated from last message receipt on each call of sendTrafficUpdates().
# 	// Mode S transmits position and track in separate messages, and altitude can also be
# 	// received from interrogations.
# 	Age                  float64   // Age of last valid position fix or last Mode-S transmission, seconds ago.
# 	AgeLastAlt           float64   // Age of last altitude message, seconds ago.
# 	Last_seen            time.Time // Time of last position update (stratuxClock) or Mode-S transmission. Used for timing out expired data.
# 	Last_alt             time.Time // Time of last altitude update (stratuxClock).
# 	Last_GnssDiff        time.Time // Time of last GnssDiffFromBaroAlt update (stratuxClock).
# 	Last_GnssDiffAlt     int32     // Altitude at last GnssDiffFromBaroAlt update.
# 	Last_speed           time.Time // Time of last velocity and track update (stratuxClock).
# 	Last_source          uint8     // Last frequency on which this target was received.
# 	ExtrapolatedPosition bool      //True if Stratux is "coasting" the target from last known position.
# 	Last_extrapolation   time.Time
# 	AgeExtrapolation     float64
# 	Lat_fix              float32   // Last real, non-extrapolated latitude
# 	Lng_fix              float32   // Last real, non-extrapolated longitude
# 	Alt_fix              int32     // Last real, non-extrapolated altitude
#
# 	BearingDist_valid    bool      // set when bearing and distance information is valid
# 	Bearing              float64   // Bearing in common.Degrees true to traffic from ownship, if it can be calculated. Units: common.Degrees.
# 	Distance             float64   // Distance to traffic from ownship, if it can be calculated. Units: meters.
# 	DistanceEstimated    float64   // Estimated distance of the target if real distance can't be calculated, Estimated from signal strength with exponential smoothing.
# 	DistanceEstimatedLastTs time.Time // Used to compute moving average
# 	ReceivedMsgs         uint64    // Number of messages received by this aircraft
# 	IsStratux            bool      // Target is equipped with a Stratux that transmits via OGN tracker
# }


logger = logging.getLogger(__name__)


class TrafficInfo(NamedTuple):
    """
    Container for traffic message received from stratux /traffic websocket endpoint.

    Reference:
    - main/traffic.go
    """
    timestamp: datetime.datetime

    gps: GPS

    # Values at 0 mean it is invalid

    altitude_m: int
    distance_m: int
    speed_kmh: int
    bearing_absolude_dg: int

    icao: str
    registration: str
    tail: str


class TrafficServiceWorker(ServiceWorker):
    """
    Traffic service interfaces with stratux and maintains a buffer of most recent traffic messages received.
    """
    # Delay between attempts to connect to stratux
    delay = datetime.timedelta(seconds=15)

    # Timeout for reading messages from websocket
    message_timeout = datetime.timedelta(seconds=5)

    def __init__(self, settings_service: SettingsService, position_service: PositionServiceWorker):
        self._settings_service = settings_service
        self._position_service = position_service

        self._traffic_info_buffer: OrderedDict[str, TrafficInfo] = OrderedDict()

        self._lock = Lock()

        self._traffic_state: Dict[str, TrafficInfo] = {}

        self.messages_seen = 0

        super().__init__()

    def trigger(self):
        """
        Attempt to connect to stratux websocket and process its messages.
        If connection is impossible or closed, it will repeat an attempt to re-connect after `delay` seconds.
        """
        endpoint = self._settings_service.get_settings().traffic_endpoint
        logger.debug(f'Trying to connect to stratux /traffic endpoint at {endpoint}')
        with connect(endpoint) as websocket:
            p = websocket.ping()
            p.wait(10)
            logger.info('Successfully connected to stratux /traffic endpoint')
            self._consume_websocket(websocket)

    def _consume_websocket(self, websocket):
        """Consume messages from websocket until shutdown or connection is unexpectedly closed"""
        while not self._shutdown:
            try:
                # If we get a lot of messages in short period of time, this loop will iterate as fast as possible through them
                message_str = websocket.recv(timeout=self.delay.total_seconds())
                logger.debug(f'Traffic message received: {message_str}')
                self._handle_traffic_message(message_str)
            except TimeoutError:
                self._update_heartbeat()
                continue
            except ConnectionClosed:
                logger.warning('Websocket connection unexpectedly closed')
                return
            except:
                logger.exception('Error receiving message from websocket')
                continue
            else:
                self._update_heartbeat()

    def _build_traffic_info(self, message: dict) -> TrafficInfo:
        position = self._position_service.get_current_position()

        traffic_info = {
            'timestamp': datetime.datetime.fromisoformat(message['Timestamp'].rstrip('Z')[:-3]),
            'icao': str(message['Icao_addr']),
            'registration': str(message['Reg']),
            'tail': str(message['Tail']),
            'gps': GPS(
                lat=message['Lat'],
                lng=message['Lng'],
            ),
            'speed_kmh': km_h(message['Speed'] if message['Speed_valid'] else 0),
        }

        altitude_m = int(meters(feet=message['Alt']))
        # Service ceiling usually is at 12 000, so anything larger than that is wonky
        if altitude_m > 15_000:
            altitude_m = 0

        traffic_info['altitude_m'] = altitude_m

        distance_m = position.distance(traffic_info['gps'])
        # It is unlikely we receive a message from that far
        if distance_m > 50_000:
            distance_m = 0

        traffic_info['distance_m'] = distance_m

        traffic_info['bearing_absolude_dg'] = position.absolute_bearing(traffic_info['gps'])

        obj = TrafficInfo(**traffic_info)

        return obj

    def _handle_traffic_message(self, message_str: str):
        """
        Process received traffic message string
        """
        self.messages_seen += 1
        message = json.loads(message_str)

        if not message['Position_valid']:
            logger.info('Skipping traffic message with invalid position')
            return

        traffic_info = self._build_traffic_info(message)

        with self._lock:
            self._traffic_state[traffic_info.icao] = traffic_info

    def get_traffic_state(self) -> Dict[str, TrafficInfo]:
        self._evict_traffic_state()
        return self._traffic_state.copy()

    def get_closest_traffic(self) -> List[TrafficInfo]:
        return sorted(self.get_traffic_state().values(), key=lambda t: t.distance_m)

    def _evict_traffic_state(self):
        track_time_s = self._settings_service.get_settings().traffic_track_time_s

        now = datetime.datetime.utcnow()
        track_time = datetime.timedelta(seconds=track_time_s)

        with self._lock:
            for icao, traffic_state in self._traffic_state.items():
                if (now - traffic_state.timestamp) > track_time:
                    logger.debug(f'{icao} has outdated')
                    self._traffic_state.pop(icao)
