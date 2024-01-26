import datetime
import logging
import time
from typing import List, NamedTuple, Dict

from geographiclib.geodesic import Geodesic

from stratux_companion.hardware_status_service import HardwareStatusService
from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.sound_service import SoundServiceWorker
from stratux_companion.traffic_service import TrafficServiceWorker, TrafficInfo
from stratux_companion.util import GPS, truncate_number, QueueConsumingServiceWorker, ServiceWorker, Throttle

logger = logging.getLogger(__name__)


class AlarmTarget(NamedTuple):
    icao: str
    gps: GPS
    alt: int

    dist: int
    heading: int
    angle: int
    speed: int


class AlarmServiceWorker(ServiceWorker):
    delay = datetime.timedelta(seconds=15)

    def __init__(self, traffic_service: TrafficServiceWorker, settings_service: SettingsService, sound_service: SoundServiceWorker, hardware_status_service: HardwareStatusService):
        self._hardware_status_service = hardware_status_service
        self._sound_service = sound_service
        self._settings_service = settings_service
        self._traffic_service = traffic_service

        self._alarming_traffic: List[TrafficInfo] = []

        self._battery_alarm_throttle = Throttle(delta=datetime.timedelta(minutes=5))

        super().__init__()

    def get_alarming_traffic(self, all_traffic: List[TrafficInfo]) -> List[TrafficInfo]:
        alarming_traffic: List[TrafficInfo] = []

        max_distance_m = self._settings_service.get_settings().max_distance_m
        max_altitude_m = self._settings_service.get_settings().max_altitude_m

        for t in all_traffic:
            if t.distance_m > max_distance_m:
                continue
            if t.altitude_m > max_altitude_m:
                continue

            alarming_traffic.append(t)

        return sorted(alarming_traffic, key=lambda t: t.distance_m)

    def alarming_traffic(self):
        return self._alarming_traffic[:]

    def monitor_traffic(self):
        all_traffic = self._traffic_service.get_closest_traffic()
        self._alarming_traffic = self.get_alarming_traffic(all_traffic)

        if len(self._alarming_traffic) > 4:
            distances = ', '.join(f'{truncate_number(t.distance_m)} meters' for t in self._alarming_traffic)
            self._sound_service.play_sound(f"{len(self._alarming_traffic)} targets, {distances}")
        elif self._alarming_traffic:
            for t in self._alarming_traffic:
                self._sound_service.play_sound(f"{truncate_number(t.distance_m)} meters away, "
                                               f"{truncate_number(t.altitude_m)} meters up, "
                                               f"at {truncate_number(t.bearing_absolude_dg)} degrees")

    def monitor_battery(self):
        if self._battery_alarm_throttle.is_throttled:
            return

        current_p = self._hardware_status_service.battery_percent

        if current_p < self._settings_service.get_settings().battery_alarm_p:
            self._sound_service.play_sound(f'Low battery: {int(current_p)} percent')

    def trigger(self):
        self.monitor_traffic()
        self.monitor_battery()
