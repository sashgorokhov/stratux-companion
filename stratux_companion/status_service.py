from stratux_companion.settings_service import SettingsService


class StatusServiceWorker:
    def __init__(self, settings_service: SettingsService):
        self._healthy = False

    def run(self):
        while True:

            self._healthy = True

    def is_healthy(self) -> bool:
        return self._healthy