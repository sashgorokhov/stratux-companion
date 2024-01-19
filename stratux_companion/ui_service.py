import datetime

from PIL import ImageFont

from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.traffic_service import TrafficServiceWorker, TrafficInstance

from PIL.ImageDraw import ImageDraw
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.lcd.device import st7735

from stratux_companion.util import ServiceWorker


class UIServiceWorker(ServiceWorker):
    delay = datetime.timedelta(seconds=0)

    def __init__(self, traffic_service: TrafficServiceWorker, settings_service: SettingsService, position_service: PositionServiceWorker):
        self._traffic_service = traffic_service
        self._settings_service = settings_service
        self._position_service = position_service

        serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
        device = st7735(
            serial_interface=serial,
            width=128,
            height=128,
            v_offset=2,
            h_offset=1,
            bgr=True,
            rotate=settings_service.get_settings().display_rotation,
            gpio_LIGHT=23,
            active_low=False
        )

        self._device = device
        self._canvas = canvas(self._device)
        self._framerate_regulator = framerate_regulator()
        self._device.clear()
        self._device.backlight(True)

        super().__init__()

    def trigger(self):
        with self._framerate_regulator:
            with self._canvas as draw:
                self._update(draw)

    def _update(self, draw: ImageDraw):
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11, encoding="unic")
        total_messages = len(self._traffic_service.get_tracked_messages())
        traffic = self._traffic_service.get_traffic()[:5]

        messages = []

        for t in traffic:
            messages.append(f"{t.icao[:3]} D:{t.distance}m A:{t.altitude}m")

        y = 3

        y = self.println(y, f'Messages: {total_messages}', draw, font)

        if not messages:
            y = self.println(y, 'No traffic detected', draw, font)

        for message in messages:
            y = self.println(y, message, draw, font)

    def println(self, y, text, draw, font):
        bbox = draw.textbbox((10, y), text=text, font=font)
        draw.text((10, y), text=text, font=font)
        y = bbox[3] + 2
        return y
