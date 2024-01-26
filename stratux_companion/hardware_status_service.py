from pathlib import Path

import board
import psutil
from adafruit_ina219 import INA219, BusVoltageRange, ADCResolution

from stratux_companion.settings_service import SettingsService


class HardwareStatusService:
    """
    Power service uses i2c INA219 DC current sensor to provide information about source power (upstream of BECs)
    """
    def __init__(self, settings_service: SettingsService):
        self._settings_service = settings_service

        i2c_bus = board.I2C()  # uses board.SCL and board.SDA
        self._ina219 = INA219(i2c_bus)

        # Configure sensor
        self._ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self._ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self._ina219.bus_voltage_range = BusVoltageRange.RANGE_16V

    @property
    def voltage(self) -> float:
        """
        Return Voltage reading
        """
        return self._ina219.bus_voltage

    @property
    def current(self) -> float:
        """
        Return Current mAh reading
        """
        return self._ina219.current

    @property
    def power(self) -> float:
        """
        Return Power Watts reading
        """
        return self._ina219.power

    @property
    def battery_percent(self) -> float:
        """
        Return current battery volatage as percents of maximum voltage
        """
        cells = self._settings_service.get_settings().battery_cells
        min_v = 3.0 * cells
        max_v = 4.2 * cells

        max_diff = max_v - min_v
        diff = max_v - self.voltage

        return 100 - (diff / max_diff) * 100

    @property
    def cpu_temp(self) -> float:
        """
        Return CPU Temperature Celsius (i am metric guy)
        """
        temp_reading = Path('/sys/class/thermal/thermal_zone0/temp').read_text()

        try:
            temp = int(temp_reading) / 1000
        except:
            temp = 0.0

        return temp

    @property
    def cpu_usage(self) -> float:
        """
        Return CPU Utilization percents
        """
        return psutil.cpu_percent()
