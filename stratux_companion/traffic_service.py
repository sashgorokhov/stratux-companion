import datetime
import json
import logging
from typing import NamedTuple, List

from stratux_companion.settings_service import SettingsService
from websockets.sync.client import connect

from stratux_companion.util import GPS

"""
{"Icao_addr":10373390,"Reg":"","Tail":"","Emitter_category":0,"SurfaceVehicleType":0,"OnGround":true,"Addr_type":3,"TargetType":4,"SignalLevel":-29.55852379121277,"SignalLevelHist":[-29.55852379121277],"Squawk":0,"Position_valid":false,"Lat":0,"Lng":0,"Alt":0,"GnssDiffFromBaroAlt":0,"AltIsGNSS":false,"NIC":0,"NACp":11,"Track":0,"TurnRate":0,"Speed":0,"Speed_valid":false,"Vvel":0,"Timestamp":"2024-01-12T04:12:52.937Z","PriorityStatus":0,"Age":50.76,"AgeLastAlt":50.76,"Last_seen":"0001-01-01T00:48:59.8Z","Last_alt":"0001-01-01T00:48:59.8Z","Last_GnssDiff":"0001-01-01T00:00:00Z","Last_GnssDiffAlt":0,"Last_speed":"0001-01-01T00:00:00Z","Last_source":1,"ExtrapolatedPosition":false,"Last_extrapolation":"0001-01-01T00:00:00Z","AgeExtrapolation":2990.56,"Lat_fix":0,"Lng_fix":0,"Alt_fix":0,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":76022.19241384401,"DistanceEstimatedLastTs":"2024-01-12T04:12:52.937Z","ReceivedMsgs":1,"IsStratux":false}
"""


logger = logging.getLogger(__name__)


class TrafficMessage(NamedTuple):
    ts: datetime.datetime

    icao: str

    gps: GPS

    alt: int
    spd: int
    hdg: int


class TrafficServiceWorker:
    def __init__(self, settings_service: SettingsService):
        self._settings_service = settings_service

        self._messages: List[TrafficMessage] = []

    def run(self):
        with connect(self._settings_service.get_settings().traffic_endpoint) as websocket:
            logger.debug('Waiting for pong from stratux websocket...')
            p = websocket.ping()
            p.wait(60)
            logger.debug('Pong received')

            while True:
                message_str = websocket.recv()
                logger.debug(f'Traffic message received: {message_str}')
                self._handle_traffic_message(message_str)

    def _handle_traffic_message(self, message_str: str):
        try:
            message = json.loads(message_str)
            traffic_message = TrafficMessage(
                ts=datetime.datetime.utcnow(),
                icao=hex(message['Icao_addr']),
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

        self._messages.append(traffic_message)

    def get_latest_messages(self) -> List[TrafficMessage]:
        traffic_track_time = datetime.timedelta(seconds=self._settings_service.get_settings().traffic_track_time_s)
        while len(self._messages):
            if (datetime.datetime.utcnow() - self._messages[0].ts) > traffic_track_time:
                logger.debug(f'{self._messages[0].icao} has outdated')
                self._messages.pop(0)
            else:
                break

        return self._messages[:]
