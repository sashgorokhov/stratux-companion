import datetime
import logging.config

from stratux_companion import config

from websockets.sync.client import connect
import logging

logger = logging.getLogger(__name__)


def handle_traffic_message(message_str: str):
    pass


def traffic_monitoring():
    with connect("ws://192.168.0.137/traffic") as websocket:
        logger.debug('Waiting for pong from stratux websocket...')
        p = websocket.ping()
        p.wait(60)
        logger.debug('Pong received')

        while True:
            message_str = websocket.recv()
            logger.debug(f'Traffic message received: {message_str}')
            handle_traffic_message(message_str)


def main():
    traffic_monitoring()


if __name__ == '__main__':
    logging.config.dictConfig(config.LOGGING_CONFIG)
    main()
