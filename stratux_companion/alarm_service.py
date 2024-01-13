import logging
import time
from typing import List, NamedTuple, Dict

from geographiclib.geodesic import Geodesic

from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.sound_service import SoundServiceWorker
from stratux_companion.traffic_service import TrafficServiceWorker, TrafficMessage
from stratux_companion.util import GPS

logger = logging.getLogger(__name__)


class AlarmTarget(NamedTuple):
    icao: str
    gps: GPS
    alt: int

    dist: int
    heading: int
    speed: int


class AlarmServiceWorker:
    def __init__(self, traffic_service: TrafficServiceWorker, settings_service: SettingsService, sound_service: SoundServiceWorker, position_service: PositionServiceWorker):
        self._position_service = position_service
        self._sound_service = sound_service
        self._settings_service = settings_service
        self._traffic_service = traffic_service

    def _get_alarm_targets(self, messages: List[TrafficMessage]) -> Dict[str, AlarmTarget]:
        targets: Dict[str, AlarmTarget] = {}
        settings = self._settings_service.get_settings()
        current_position = self._position_service.get_current_position()

        for message in messages:
            # TODO: Handle invalid GPS
            distance = message.gps - current_position
            # if distance > settings.max_distance_m:
            #     if distance > 50_000:
            #         logger.warning(f'Wonky distance for message {message}: home at {current_position}, distance is {distance}')
            #     continue
            # if message.alt > settings.max_altitude_m:
            #     continue

            # TODO Calculate heading direction alarm

            targets[message.icao] = AlarmTarget(
                icao=message.icao,
                gps=message.gps,
                alt=int(message.alt),
                dist=int(distance),
                heading=message.hdg,
                speed=message.spd,
            )
        return targets

    def _angle(self, pos1: GPS, pos2: GPS) -> int:
        result = Geodesic.Inverse(pos1.lat, pos1.lng, pos2.lat, pos2.lng)
        return int(result['azi1'])

    def run(self):
        while True:
            current_position = self._position_service.get_current_position()
            latest_messages = self._traffic_service.get_latest_messages()
            alarm_targets = self._get_alarm_targets(latest_messages)

            if len(alarm_targets):
                logger.info(f'Found {len(alarm_targets)} targets to alarm: {alarm_targets.keys()}')

                for target in alarm_targets.values():
                    alarm = f"{int(target.dist)} meters away, {int(target.alt)} meters up, at {self._angle(current_position, target.gps)} degrees"
                    self._sound_service.play_sound(alarm)

            time.sleep(5)
