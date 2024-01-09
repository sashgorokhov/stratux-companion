from stratux_companion.settings_interface import SettingsInterface
from stratux_companion.sound_interface import SoundInterface
from stratux_companion.traffic_interface import TrafficInterface


class AlarmInterface:
    def __init__(self, traffic_interface: TrafficInterface, settings_interface: SettingsInterface, sound_interface: SoundInterface):
        self._sound_interface = sound_interface
        self._settings_interface = settings_interface
        self._traffic_interface = traffic_interface

    def run(self):
        pass
