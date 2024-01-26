import logging.config
from threading import Thread
from typing import Callable

from stratux_companion import config
from stratux_companion.alarm_service import AlarmServiceWorker
from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.hardware_status_service import HardwareStatusService
from stratux_companion.settings_service import SettingsService
from stratux_companion.sound_service import SoundServiceWorker
from stratux_companion.traffic_service import TrafficServiceWorker
from stratux_companion.ui_service import UIServiceWorker

logger = logging.getLogger(__name__)


def run_and_wait(*targets: Callable[[], None]):
    threads = []

    for target in targets:
        threads.append(Thread(target=target))
        threads[-1].start()

    for thread in threads:
        thread.join()


def main():
    settings_service = SettingsService(
        settings_file=config.SETTINGS_FILE
    )

    hardware_status_service = HardwareStatusService(
        settings_service=settings_service
    )

    position_service = PositionServiceWorker(
        settings_service=settings_service
    )
    traffic_service = TrafficServiceWorker(
        settings_service=settings_service,
        position_service=position_service,
    )

    sound_service = SoundServiceWorker(
        settings_service=settings_service
    )
    alarm_interface = AlarmServiceWorker(
        settings_service=settings_service,
        traffic_service=traffic_service,
        sound_service=sound_service,
        hardware_status_service=hardware_status_service,
    )


    ui_service = UIServiceWorker(
        settings_service=settings_service,
        traffic_service=traffic_service,
        position_service=position_service,
        alarm_service=alarm_interface,
        hardware_status_service=hardware_status_service,
    )

    run_and_wait(
        ui_service.run,
        traffic_service.run,
        sound_service.run,
        alarm_interface.run,
        position_service.run,
    )


if __name__ == '__main__':
    logging.config.dictConfig(config.LOGGING_CONFIG)
    main()
