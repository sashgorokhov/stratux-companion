import logging
from pathlib import Path
from threading import Lock
from typing import Literal

import pydantic

from stratux_companion.util import GPS

logger = logging.getLogger(__name__)


class Settings(pydantic.BaseModel):
    traffic_endpoint: str = 'ws://192.168.10.1/traffic'

    traffic_track_time_s: int = 30

    mute: bool = False

    default_position: GPS = GPS(
        lat=30.4509056,
        lng=-97.6827249,
    )

    max_distance_m: int = 10_000
    max_altitude_m: int = 3_000

    display_rotation: Literal[0, 1, 2, 3] = 0


class Settings_Local(Settings):
    traffic_endpoint = 'ws://192.168.0.137/traffic'


class SettingsService:
    def __init__(self, settings_file: Path):
        self._settings_file = settings_file
        self._settings = self._load_settings()
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
