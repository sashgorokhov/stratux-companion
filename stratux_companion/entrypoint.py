import logging.config
from threading import Thread
from typing import Callable

from luma.core.interface.serial import spi
from luma.lcd.device import st7735

from stratux_companion import config
from stratux_companion.alarm_interface import AlarmInterface
from stratux_companion.settings_interface import SettingsInterface
from stratux_companion.sound_interface import SoundInterface
from stratux_companion.traffic_interface import TrafficInterface
from stratux_companion.user_interface import UserInterface

logger = logging.getLogger(__name__)


def run_and_wait(*targets: Callable[[], None]):
    threads = []

    for target in targets:
        threads.append(Thread(target=target))
        threads[-1].start()

    for thread in threads:
        thread.join()


def main():
    settings_interface = SettingsInterface(
        settings_file=config.SETTINGS_FILE
    )
    traffic_interface = TrafficInterface(
        settings_interface=settings_interface
    )

    serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
    device = st7735(serial, width=128, height=128, v_offset=2, h_offset=1, bgr=True, rotate=1)

    user_interface = UserInterface(
        device=device,
        settings_interface=settings_interface,
        traffic_interface=traffic_interface
    )
    sound_interface = SoundInterface(
        settings_interface=settings_interface
    )
    alarm_interface = AlarmInterface(
        settings_interface=settings_interface,
        traffic_interface=traffic_interface,
        sound_interface=sound_interface
    )

    run_and_wait(
        user_interface.run,
        traffic_interface.run,
        sound_interface.run,
        alarm_interface.run
    )


if __name__ == '__main__':
    logging.config.dictConfig(config.LOGGING_CONFIG)
    main()
