from stratux_companion.settings_interface import SettingsInterface
from stratux_companion.traffic_service import TrafficServiceWorker
import time
from typing import Tuple

from PIL.ImageDraw import ImageDraw
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.lcd.device import st7735


class MenuItem:
    def __init__(self, text):
        self.text = text
        self.selected = False

    def draw(self, xy: Tuple[int, int], draw: ImageDraw, font):
        bbox = draw.textbbox(xy, self.text, font=font)

        fill = (30, 30, 30)
        outline = 'yellow'

        if self.selected:
            if int(time.monotonic() * 5) % 2:
                fill = (60, 60, 60)
            else:
                fill = (30, 30, 30)

        draw.rectangle((bbox[0] - 5, bbox[1] - 5, bbox[2] + 5, bbox[3] + 5), fill=fill, outline=outline)
        draw.text(xy, self.text, font=font)

        return bbox[3]


class UIServiceWorker:
    def __init__(self, device, traffic_interface: TrafficServiceWorker, settings_interface: SettingsInterface):
        self._device = device
        self._traffic_interface = traffic_interface
        self._settings_interface = settings_interface

        self._canvas = canvas(self._device)
        self._framerate_regulator = framerate_regulator()
        self._device.clear()

        self.menus = [
            MenuItem('config'),
            MenuItem('radar'),
        ]

    def run(self):
        while True:
            with self._framerate_regulator:
                with self._canvas as draw:
                    self._update(draw)

    def _update(self, draw: ImageDraw):
        font = draw.getfont()

        x = self._device.width // 2 - draw.textbbox((0, 0), self.menus[0].text, font=font)[2] // 2
        y = 10

        self.menus[0].selected = True

        for menu in self.menus:
            height = menu.draw((x, y), draw, font)

            y += height + 5 + 5

        draw.rectangle((0, self._device.height - 13, self._device.width, self._device.height), fill=(20, 20, 20))
        draw.text((5, self._device.height - 12), 'Stratux companion', font=font)


if __name__ == '__main__':
    serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
    device = st7735(serial, width=128, height=128, v_offset=2, h_offset=1, bgr=True, rotate=1)
    ui = UIServiceWorker(device)
    ui.run()
