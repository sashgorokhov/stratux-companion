import logging
import time

from stratux_companion.settings_service import SettingsService
from stratux_companion.sound_service import SoundServiceWorker
from stratux_companion.traffic_service import TrafficServiceWorker


logger = logging.getLogger(__name__)


class AlarmServiceWorker:
    def __init__(self, traffic_service: TrafficServiceWorker, settings_service: SettingsService, sound_service: SoundServiceWorker):
        self._sound_service = sound_service
        self._settings_service = settings_service
        self._traffic_service = traffic_service

    def run(self):
        while True:
            latest_messages = self._traffic_service.get_latest_messages()
            logger.debug(f'Latest messages: {[m.icao for m in latest_messages]}')

            alarm = f"{len({m.icao for m in latest_messages})} targets around"

            self._sound_service.play_sound(alarm)

            time.sleep(5)
