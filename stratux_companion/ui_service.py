import datetime

from PIL import ImageFont

from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.traffic_service import TrafficServiceWorker


from PIL.ImageDraw import ImageDraw
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.lcd.device import st7735, backlit_device

from stratux_companion.util import ServiceWorker


# class MenuItem:
#     def __init__(self, text):
#         self.text = text
#         self.selected = False
#
#     def draw(self, xy: Tuple[int, int], draw: ImageDraw, font):
#         bbox = draw.textbbox(xy, self.text, font=font)
#
#         fill = (30, 30, 30)
#         outline = 'yellow'
#
#         if self.selected:
#             if int(time.monotonic() * 5) % 2:
#                 fill = (60, 60, 60)
#             else:
#                 fill = (30, 30, 30)
#
#         draw.rectangle((bbox[0] - 5, bbox[1] - 5, bbox[2] + 5, bbox[3] + 5), fill=fill, outline=outline)
#         draw.text(xy, self.text, font=font)
#
#         return bbox[3]


class UIServiceWorker(ServiceWorker):
    delay = datetime.timedelta(seconds=0)

    def __init__(self, device: backlit_device, traffic_service: TrafficServiceWorker, settings_service: SettingsService, position_service: PositionServiceWorker):
        self._device = device
        self._traffic_service = traffic_service
        self._settings_service = settings_service
        self._position_service = position_service

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
        font = ImageFont.load_default(size=10)
        traffic = self._traffic_service.get_traffic()[:5]

        messages = []

        for t in traffic:
            messages.append(f"{t.icao[:3]} D:{t.distance}m A:{t.altitude}m")

        y = 10
        x = 3

        if not messages:
            messages.append("No traffic detected")

        for message in messages:
            bbox = draw.textbbox((x, y), text=message, font=font)
            draw.text((x, y), text=message, font=font)

            y += bbox[3] + 5

    # def _update(self, draw: ImageDraw):
    #     font = draw.getfont()
    #
    #     x = self._device.width // 2 - draw.textbbox((0, 0), self.menus[0].text, font=font)[2] // 2
    #     y = 10
    #
    #     self.menus[0].selected = True
    #
    #     for menu in self.menus:
    #         height = menu.draw((x, y), draw, font)
    #
    #         y += height + 5 + 5
    #
    #     draw.rectangle((0, self._device.height - 13, self._device.width, self._device.height), fill=(20, 20, 20))
    #     draw.text((5, self._device.height - 12), 'Stratux companion', font=font)
