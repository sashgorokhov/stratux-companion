import datetime
import json
import logging
from typing import NamedTuple, List

from stratux_companion.settings_service import SettingsService
from websockets.sync.client import connect

from stratux_companion.util import GPS

"""
{"Icao_addr":11030261,"Reg":"N6340E","Tail":"N6340E","Emitter_category":1,"SurfaceVehicleType":0,"OnGround":false,"Addr_type":0,"TargetType":1,"SignalLevel":-28.873949984654253,"SignalLevelHist":null,"Squawk":3655,"Position_valid":true,"Lat":30.346046,"Lng":-97.770645,"Alt":4300,"GnssDiffFromBaroAlt":75,"AltIsGNSS":false,"NIC":8,"NACp":9,"Track":198,"TurnRate":0,"Speed":99,"Speed_valid":true,"Vvel":0,"Timestamp":"2024-01-12T05:30:20.777200261Z","PriorityStatus":0,"Age":59.72,"AgeLastAlt":59.72,"Last_seen":"0001-01-01T00:20:29.26Z","Last_alt":"0001-01-01T00:20:29.26Z","Last_GnssDiff":"0001-01-01T00:20:29.26Z","Last_GnssDiffAlt":4300,"Last_speed":"0001-01-01T00:20:29.26Z","Last_source":2,"ExtrapolatedPosition":true,"Last_extrapolation":"0001-01-01T00:21:28.75Z","AgeExtrapolation":0.23,"Lat_fix":30.372026,"Lng_fix":-97.76068,"Alt_fix":4300,"BearingDist_valid":false,"Bearing":0,"Distance":0,"DistanceEstimated":0,"DistanceEstimatedLastTs":"0001-01-01T00:00:00Z","ReceivedMsgs":261,"IsStratux":false}
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
