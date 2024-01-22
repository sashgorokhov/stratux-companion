import datetime

from PIL import ImageFont, Image, ImageDraw

from stratux_companion.alarm_service import AlarmServiceWorker
from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.settings_service import SettingsService
from stratux_companion.traffic_service import TrafficServiceWorker

from luma.core.interface.serial import spi
from luma.core.sprite_system import framerate_regulator
from luma.lcd.device import st7735

from stratux_companion.util import ServiceWorker


class Screen:
    """
    Screen incapsulates logic of drawing specific things on the display.
    """
    def __init__(self, *, device):
        self._image = Image.new(mode=device.mode, size=device.size)
        self._draw = ImageDraw.Draw(self._image)

        self._font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11, encoding="unic")

    def update(self):
        self._clear()

    def _clear(self):
        self._draw.rectangle((0, 0, self._image.width, self._image.height), fill='black')

    @property
    def image(self) -> Image.Image:
        return self._image


class LinedScreen(Screen):
    """
    Lined screen allows displaying text in lines and tracks each line position itself.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._x_offset = 3
        self._y_offset = 3

    def update(self):
        super().update()
        self._y_offset = 3

        for line in self.get_lines():
            self.println(line)

    def get_lines(self):
        raise NotImplementedError()

    def println(self, text):
        bbox = self._draw.textbbox((self._x_offset, self._y_offset), text=text, font=self._font)
        self._draw.text((self._x_offset, self._y_offset), text=text, font=self._font)
        self._y_offset = bbox[3] + 2


class TrafficScreen(LinedScreen):
    """
    Traffic screen shows all detected traffic
    """

    max_traffic = 5
    
    def __init__(self, traffic_service: TrafficServiceWorker, **kwargs,):
        self._traffic_service = traffic_service
        
        super().__init__(**kwargs)

    def get_lines(self):
        traffic = self._traffic_service.get_closest_traffic()

        lines = [
            f'Messages: {self._traffic_service.messages_seen}'
        ]

        if not traffic:
            lines.append('No traffic detected')
        else:
            for t in traffic[:self.max_traffic]:
                lines.append(f"{t.icao[:3]} D:{t.distance_m}m A:{t.altitude_m}m")

        return lines


class AlarmScreen(LinedScreen):
    """
    Alarm screen shows currently alarming traffic
    """
    def __init__(self, alarm_service: AlarmServiceWorker, **kwargs):
        self._alarm_service = alarm_service
        super().__init__(**kwargs)

    def get_lines(self):
        alarming_traffic = self._alarm_service.alarming_traffic()

        lines = [
            f'Alarms: {len(alarming_traffic)}'
        ]

        for t in alarming_traffic:
            lines.append(f"{t.registration if t.registration else t.icao[:3]} D:{t.distance_m}m A:{t.altitude_m}m")

        return lines


class UIServiceWorker(ServiceWorker):
    """
    UI Service worker manages display. It uses Screen instances to output different information.
    """
    # Framerate regulator will do the delays
    delay = datetime.timedelta(seconds=0)

    _screen: Screen

    def __init__(self, traffic_service: TrafficServiceWorker, settings_service: SettingsService, position_service: PositionServiceWorker, alarm_service: AlarmServiceWorker):
        self._traffic_service = traffic_service
        self._settings_service = settings_service
        self._position_service = position_service
        self._alarm_service = alarm_service

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
        self._framerate_regulator = framerate_regulator()
        self._device.clear()
        self._device.backlight(True)

        self.set_traffic_screen()

        super().__init__()

    def set_traffic_screen(self):
        self._screen = TrafficScreen(device=self._device, traffic_service=self._traffic_service)

    def set_alarm_screen(self):
        self._screen = AlarmScreen(device=self._device, alarm_service=self._alarm_service)

    def trigger(self):
        with self._framerate_regulator:
            if self._alarm_service.alarming_traffic():
                self.set_alarm_screen()
            else:
                self.set_traffic_screen()

            self._screen.update()
            self._device.display(self._screen.image)
