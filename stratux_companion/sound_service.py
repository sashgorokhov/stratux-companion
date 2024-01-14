import datetime
import logging
import time
from queue import Queue

import pyttsx3

from stratux_companion.settings_service import SettingsService
from stratux_companion.util import ServiceWorker

logger = logging.getLogger(__name__)


# TODO:
#  - message deduplication
#  - system messages queue, high priority
#  - traffic messages queue, low priority
#  - support for beeps

class SoundServiceWorker(ServiceWorker):
    """
    Sound service interfaces with sound system and converts text messages into sound messages
    """

    delay = datetime.timedelta(seconds=0.5)

    def __init__(self, settings_service: SettingsService):
        self._settings_service = settings_service
        self._queue = Queue()
        self.play_sound('Sound enabled')

        super().__init__()

    def trigger(self):
        if not self._queue.empty():
            ts, text = self._queue.get_nowait()
            if (datetime.datetime.utcnow() - ts) > datetime.timedelta(seconds=5):
                return
            self._play_sound(text)

    def play_sound(self, text: str):
        self._queue.put_nowait((datetime.datetime.utcnow(), text))

    def _play_sound(self, text: str):
        logger.debug(f'Speech text: {text}')
        if not self._settings_service.get_settings().mute:
            pyttsx3.speak(text)
