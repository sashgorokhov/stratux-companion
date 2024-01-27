from pathlib import Path

import pytest

from stratux_companion.hardware_status_service import HardwareStatusService
from stratux_companion.settings_service import SettingsService


@pytest.fixture
def settings_file(tmp_path):
    return Path(tmp_path) / 'settings.json'


@pytest.fixture()
def settings_service(settings_file):
    return SettingsService(settings_file)


@pytest.fixture()
def hardware_status_service(settings_service):
    return HardwareStatusService(settings_service)

