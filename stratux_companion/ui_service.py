import datetime
import time

import psutil
from PIL import ImageFont, Image, ImageDraw

from stratux_companion.alarm_service import AlarmServiceWorker
from stratux_companion.position_service import PositionServiceWorker
from stratux_companion.hardware_status_service import HardwareStatusService
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

        for t in alarming_traffic[:5]:
            lines.append(f"{t.registration if t.registration else t.icao[:3]} D:{t.distance_m}m A:{t.altitude_m}m")

        return lines


class StatusScreen(LinedScreen):
    """
    Status screen displays current cpu, temperature, battery readings
    """
    def __init__(self, position_service: PositionServiceWorker, hardware_status_service: HardwareStatusService, **kwargs):
        self._position_service = position_service
        self._hardware_status_service = hardware_status_service

        self._power_readings = []

        super().__init__(**kwargs)

    def get_lines(self):
        position_info = self._position_service.position_info()
        gps = self._position_service.get_current_position()

        battery_p = round(self._hardware_status_service.battery_percent, 0)
        volts = round(self._hardware_status_service.voltage, 1)
        watts = round(self._hardware_status_service.power, 1)
        temp = round(self._hardware_status_service.cpu_temp, 0)
        cpu = round(self._hardware_status_service.cpu_usage, 0)

        return [
            f'Lat: {gps.lat}',
            f'Lng: {gps.lng}',
            f'Sats: {position_info.satellites}',
            f'CPU: {cpu}%',
            f'Temp: {temp}C',
            f'Batt: {battery_p}% {volts}v ',
            f'  {watts}W',
        ]

    def update(self):
        super().update()

        # self.render_power_graph()

    # def render_power_graph(self):
    #     dot_size = 2
    #     width = 100
    #     height = 30
    #     max_readings = width // dot_size
    #     max_read_value = 15
    #
    #     start_x, start_y = self._x_offset, self._y_offset
    #     end_x = start_x + width
    #     end_y = start_y + height
    #
    #     self._power_readings.append(self._hardware_status_service.power)
    #     if len(self._power_readings) > max_readings:
    #         self._power_readings.pop(0)
    #
    #     slope = height / max_read_value
    #
    #     self._draw.rectangle((start_x, start_y, end_x, end_y), outline='red')
    #
    #     for n, reading in enumerate(self._power_readings):
    #         x = start_x + n*2
    #         y = end_y - round(slope * reading)
    #         self._draw.rectangle((x, y, x + dot_size // 2, y + dot_size // 2), fill='red')


class UIServiceWorker(ServiceWorker):
    """
    UI Service worker manages display. It uses Screen instances to output different information.
    """
    # Framerate regulator will do the delays
    delay = datetime.timedelta(seconds=0)

    _screen: Screen

    def __init__(self, traffic_service: TrafficServiceWorker, settings_service: SettingsService, position_service: PositionServiceWorker, alarm_service: AlarmServiceWorker, hardware_status_service: HardwareStatusService):
        self._traffic_service = traffic_service
        self._settings_service = settings_service
        self._position_service = position_service
        self._alarm_service = alarm_service
        self._hardware_status_service = hardware_status_service

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
        self._framerate_regulator = framerate_regulator(fps=5)
        self._device.clear()
        self._device.backlight(True)

        self._screen_carousel_t = time.time()

        self.set_traffic_screen()

        super().__init__()

    def set_traffic_screen(self):
        self._screen = TrafficScreen(device=self._device, traffic_service=self._traffic_service)

    def set_alarm_screen(self):
        self._screen = AlarmScreen(device=self._device, alarm_service=self._alarm_service)

    def set_status_screen(self):
        self._screen = StatusScreen(device=self._device, position_service=self._position_service, hardware_status_service=self._hardware_status_service)

    def trigger(self):
        with self._framerate_regulator:
            self._switch_screens()
            self._screen.update()
            self._device.display(self._screen.image)

    def _switch_screens(self):
        if self._alarm_service.alarming_traffic():
            self.set_alarm_screen()
        else:
            if time.time() - self._screen_carousel_t > 10:
                self._screen_carousel_t = time.time()
                if isinstance(self._screen, TrafficScreen):
                    self.set_status_screen()
                else:
                    self.set_traffic_screen()
