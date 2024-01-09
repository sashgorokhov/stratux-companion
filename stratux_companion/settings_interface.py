import json
import logging
from pathlib import Path
from threading import Lock

import pydantic


logger = logging.getLogger(__name__)


class Settings(pydantic.BaseModel):
    traffic_endpoint: str = 'ws://127.0.0.1/traffic'


class Settings_Local(Settings):
    traffic_endpoint = 'ws://192.168.0.137/traffic'


class SettingsInterface:
    def __init__(self, settings_file: Path):
        self._settings = self._load_settings()
        self._settings_file = settings_file
        self._lock = Lock()

        logger.debug(f'Initialized settings at {settings_file}: {self._settings}')

    def _persist_settings(self):
        self._settings_file.write_text(self._settings.json())

    def _load_settings(self) -> Settings:
        try:
            return Settings.parse_file(self._settings_file)
        except:
            logger.exception(f'Error while reading settings from {self._settings_file}')
            return self._reset_settings()

    def _reset_settings(self) -> Settings:
        self._settings = Settings()
        self._persist_settings()
        return self._settings

    def get_settings(self) -> Settings:
        return self._settings

    def set_settings(self, settings: Settings):
        with self._lock:
            self._persist_settings()
            self._settings = settings
