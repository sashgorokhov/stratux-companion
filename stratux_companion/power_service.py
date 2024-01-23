import board
from adafruit_ina219 import INA219, BusVoltageRange, ADCResolution


class PowerService:
    """
    Power service uses i2c INA219 DC current sensor to provide information about source power (upstream of BECs)
    """
    def __init__(self):
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
