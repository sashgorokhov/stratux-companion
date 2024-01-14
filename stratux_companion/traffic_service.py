import datetime
import json
import logging
from threading import Lock
from typing import NamedTuple, List, Dict

from websockets import ConnectionClosed
from websockets.sync.client import connect

from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.util import GPS, ServiceWorker

"""
{"Icao_addr":11030261,"Reg":"N6340E","Tail":"N6340E","Emitter_category":1,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-28.873949984654253,"SignalLevelHist":null,"Squawk":3655,"Position_valid":true,"Lat":30.346046,"Lng":-97.770645,"Alt":4300,"GnssDiffFromBaroAlt":75,"AltIsGNSS":false,"NIC":8,"NACp":9,"Track":198,"TurnRate":0,"Speed":99,"Speed_valid":true,"Vvel":0,"Timestamp":"2024-01-12T05:30:20.777200261Z","PriorityStatus":0,"Age":59.72,"AgeLastAlt":59.72,"Last_seen":"0001-01-01T00:20:29.26Z","Last_alt":"0001-01-01T00:20:29.26Z","Last_GnssDiff":"0001-01-01T00:20:29.26Z","Last_GnssDiffAlt":4300,"Last_speed":"0001-01-01T00:20:29.26Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T00:21:28.75Z","AgeExtrapolation":0.23,"Lat_fix":30.372026,"Lng_fix":-97.76068,"Alt_fix":4300,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":261,"IsStratux":false}
{"Icao_addr":5883938,"Reg":"","Tail":"","Emitter_category":0,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-37.72113295386327,"SignalLevelHist":null,"Squawk":0,"Position_valid":true,"Lat":34.019497,"Lng":100.82681,"Alt":116957,"GnssDiffFromBaroAlt":0,"AltIsGNSS":true,"NIC":10,"NACp":0,"Track":149,"TurnRate":0,"Speed":4269,"Speed_valid":true,"Vvel":19520,"Timestamp":"2024-01-12T06:02:23.097187757Z","PriorityStatus":0,"Age":59.4,"AgeLastAlt":59.4,"Last_seen":"0001-01-01T00:52:31.58Z","Last_alt":"0001-01-01T00:52:31.58Z","Last_GnssDiff":"0001-01-01T00:00:00Z","Last_GnssDiffAlt":0,"Last_speed":"0001-01-01T00:52:31.58Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T00:53:30.91Z","AgeExtrapolation":0.07,"Lat_fix":35.024628,"Lng_fix":100.09388,"Alt_fix":97675,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":1,"IsStratux":false}
{"Icao_addr":11030261,"Reg":"N6340E","Tail":"N6340E","Emitter_category":1,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-27.95880017344075,"SignalLevelHist":null,"Squawk":2557,"Position_valid":true,"Lat":30.540617,"Lng":-97.71647,"Alt":5400,"GnssDiffFromBaroAlt":25,"AltIsGNSS":false,"NIC":8,"NACp":9,"Track":30,"TurnRate":0,"Speed":106,"Speed_valid":true,"Vvel":0,"Timestamp":"2024-01-12T07:10:34.301879322Z","PriorityStatus":0,"Age":4.2,"AgeLastAlt":4.2,"Last_seen":"0001-01-01T02:00:42.73Z","Last_alt":"0001-01-01T02:00:42.73Z","Last_GnssDiff":"0001-01-01T02:00:33.91Z","Last_GnssDiffAlt":5400,"Last_speed":"0001-01-01T02:00:42.73Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T02:00:46.36Z","AgeExtrapolation":0.57,"Lat_fix":30.539074,"Lng_fix":-97.7175,"Alt_fix":5400,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":55,"IsStratux":false}
"""


logger = logging.getLogger(__name__)


class TrafficMessage(NamedTuple):
    """
    Container for traffic message received from stratux /traffic websocket endpoint
    """
    ts: datetime.datetime

    icao: str

    gps: GPS

    alt: int
    spd: int
    hdg: int


class TrafficInstance(NamedTuple):
    """
    Processed information of specific traffic entity (by icao address) with calculated supplementary information like distance and angle
    """
    gps: GPS
    distance: int
    altitude: int
    speed: int
    heading: int
    angle: int
    icao: str


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

        self._messages: List[TrafficMessage] = []

        self._lock = Lock()

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

    def _handle_traffic_message(self, message_str: str):
        """
        Process received traffic message string
        """
        try:
            message = json.loads(message_str)
            traffic_message = TrafficMessage(
                ts=datetime.datetime.utcnow(),
                icao=str(message['Icao_addr']),
                gps=GPS(
                    lat=message['Lat'],
                    lng=message['Lng'],
                ),
                alt=message['Alt'],
                spd=message['Speed'],
                hdg=message['Track'],
            )
        except:
            logger.exception(f'Error decoding message: {message_str}')
            return

        if not traffic_message.gps.is_valid:
            logger.warning(f'Skipping traffic message with invalid GPS: {traffic_message}')
            return

        with self._lock:
            self._messages.append(traffic_message)

    def get_tracked_messages(self) -> List[TrafficMessage]:
        """
        Return latest messages (based on traffic_track_time_s)
        """
        with self._lock:
            traffic_track_time = datetime.timedelta(seconds=self._settings_service.get_settings().traffic_track_time_s)
            now = datetime.datetime.utcnow()
            while len(self._messages):
                if (now - self._messages[0].ts) > traffic_track_time:
                    logger.debug(f'{self._messages[0].icao} has outdated')
                    self._messages.pop(0)
                else:
                    break

            return self._messages[:]

    def get_traffic(self) -> List[TrafficInstance]:
        """
        Return list of latest TrafficInstances processed from current message buffer
        """
        traffic: Dict[str, TrafficInstance] = {}
        position = self._position_service.get_current_position()

        for message in self.get_tracked_messages():
            traffic[message.icao] = TrafficInstance(
                gps=message.gps,
                distance=int(position.distance(message.gps)),
                angle=int(position.angle(message.gps)),
                heading=int(message.hdg),
                altitude=int(message.alt),
                icao=message.icao,
                speed=int(message.spd)
            )

        return sorted(traffic.values(), key=lambda t: t.distance)
