import logging
import time
from queue import Queue

import pyttsx3

from stratux_companion.settings_service import SettingsService

logger = logging.getLogger(__name__)


class SoundServiceWorker:
    def __init__(self, settings_service: SettingsService):
        self._settings_service = settings_service
        self._queue = Queue()
        self.play_sound('Initialized')

    def run(self):
        while True:
            if not self._queue.empty():
                text = self._queue.get_nowait()
                self._play_sound(text)

            time.sleep(0.5)

    def play_sound(self, text: str):
        self._queue.put_nowait(text)

    def _play_sound(self, text: str):
        logger.debug(f'Speech text: {text}')
        if not self._settings_service.get_settings().mute:
            pyttsx3.speak(text)
