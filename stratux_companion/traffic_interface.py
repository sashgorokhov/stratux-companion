import logging

from stratux_companion.settings_interface import SettingsInterface
from websockets.sync.client import connect


logger = logging.getLogger(__name__)


class TrafficInterface:
    def __init__(self, settings_interface: SettingsInterface):
        self._settings_interface = settings_interface

    def run(self):
        with connect(self._settings_interface.get_settings().traffic_endpoint) as websocket:
            logger.debug('Waiting for pong from stratux websocket...')
            p = websocket.ping()
            p.wait(60)
            logger.debug('Pong received')

            while True:
                message_str = websocket.recv()
                logger.debug(f'Traffic message received: {message_str}')
                self.handle_traffic_message(message_str)

    def handle_traffic_message(self, message_str: str):
        pass
