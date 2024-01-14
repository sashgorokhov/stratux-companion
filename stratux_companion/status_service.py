from stratux_companion.settings_service import SettingsService
from stratux_companion.util import ServiceWorker


class StatusServiceWorker(ServiceWorker):
    def __init__(self, settings_service: SettingsService):
        self._healthy = False

        super().__init__()

    def trigger(self):
        self._healthy = True

    def is_healthy(self) -> bool:
        return self._healthy
