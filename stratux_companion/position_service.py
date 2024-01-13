from typing import Optional

from stratux_companion.settings_service import SettingsService
from stratux_companion.util import GPS


class PositionServiceWorker:
    def __init__(self, settings_service: SettingsService):
        self._current_position: Optional[GPS] = None
        self._settings_service = settings_service

    def run(self):
        pass

    def get_current_position(self) -> GPS:
        if self._current_position is None:
            return self._settings_service.get_settings().default_position
