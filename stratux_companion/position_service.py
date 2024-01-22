import datetime
from typing import Optional

from stratux_companion.settings_service import SettingsService
from stratux_companion.util import GPS, ServiceWorker


class PositionServiceWorker(ServiceWorker):
    """
    Position service knows current GPS location coordinates and interfaces with onboard GPS unit.
    """

    delay = datetime.timedelta(seconds=30)

    def __init__(self, settings_service: SettingsService):
        self._current_position: Optional[GPS] = None
        self._settings_service = settings_service

        super().__init__()

    def get_current_position(self) -> GPS:
        if self._current_position is None:
            return self._settings_service.get_settings().default_position

    def trigger(self):
        pass
