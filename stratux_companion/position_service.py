import datetime
import logging
from typing import Optional, NamedTuple

import requests
from geopy.units import meters

from stratux_companion.settings_service import SettingsService
from stratux_companion.sound_service import SoundServiceWorker, Beeps
from stratux_companion.util import GPS, ServiceWorker

logger = logging.getLogger(__name__)

#
# type SituationData struct {
# 	// From GPS.
# 	muGPS                       *sync.Mutex
# 	muGPSPerformance            *sync.Mutex
# 	muSatellite                 *sync.Mutex
# 	GPSLastFixSinceMidnightUTC  float32
# 	GPSLatitude                 float32
# 	GPSLongitude                float32
# 	GPSFixQuality               uint8
# 	GPSHeightAboveEllipsoid     float32 // GPS height above WGS84 ellipsoid, ft. This is specified by the GDL90 protocol, but most EFBs use MSL altitude instead. HAE is about 70-100 ft below GPS MSL altitude over most of the US.
# 	GPSGeoidSep                 float32 // geoid separation, ft, MSL minus HAE (used in altitude calculation)
# 	GPSSatellites               uint16  // satellites used in solution
# 	GPSSatellitesTracked        uint16  // satellites tracked (almanac data received)
# 	GPSSatellitesSeen           uint16  // satellites seen (signal received)
# 	GPSHorizontalAccuracy       float32 // 95% confidence for horizontal position, meters.
# 	GPSNACp                     uint8   // NACp categories are defined in AC 20-165A
# 	GPSAltitudeMSL              float32 // Feet MSL
# 	GPSVerticalAccuracy         float32 // 95% confidence for vertical position, meters
# 	GPSVerticalSpeed            float32 // GPS vertical velocity, feet per second
# 	GPSLastFixLocalTime         time.Time
# 	GPSTrueCourse               float32
# 	GPSTurnRate                 float64 // calculated GPS rate of turn, degrees per second
# 	GPSGroundSpeed              float64
# 	GPSLastGroundTrackTime      time.Time
# 	GPSTime                     time.Time
# 	GPSLastGPSTimeStratuxTime   time.Time // stratuxClock time since last GPS time received.
# 	GPSLastValidNMEAMessageTime time.Time // time valid NMEA message last seen
# 	GPSLastValidNMEAMessage     string    // last NMEA message processed.
# 	GPSPositionSampleRate       float64   // calculated sample rate of GPS positions
#
# 	// From pressure sensor.
# 	muBaro                  *sync.Mutex
# 	BaroTemperature         float32
# 	BaroPressureAltitude    float32
# 	BaroVerticalSpeed       float32
# 	BaroLastMeasurementTime time.Time
# 	BaroSourceType          uint8
#
# 	// From AHRS source.
# 	muAttitude           *sync.Mutex
# 	AHRSPitch            float64
# 	AHRSRoll             float64
# 	AHRSGyroHeading      float64
# 	AHRSMagHeading       float64
# 	AHRSSlipSkid         float64
# 	AHRSTurnRate         float64
# 	AHRSGLoad            float64
# 	AHRSGLoadMin         float64
# 	AHRSGLoadMax         float64
# 	AHRSLastAttitudeTime time.Time
# 	AHRSStatus           uint8
# }


class PositionInfo(NamedTuple):
    altitude_msl_m: int  # MSL Altitude
    altitude_hae_m: int  # Height above WGS84 ellipsoid
    satellites: int

    @property
    def is_valid(self):
        return self.satellites > 0


class PositionServiceWorker(ServiceWorker):
    """
    Position service interfaces with startux /getSituation endpoint and provides current GPS coordinates
    """

    # Delay between attempts to connect to stratux
    delay = datetime.timedelta(seconds=30)

    def __init__(self, settings_service: SettingsService, sound_service: SoundServiceWorker):
        self._current_position: Optional[GPS] = None
        self._position_info = PositionInfo(
            altitude_hae_m=0,
            altitude_msl_m=0,
            satellites=0
        )
        self._settings_service = settings_service
        self._sound_service = sound_service

        self._session = requests.Session()

        super().__init__()

    def trigger(self):
        situation_response = self._session.get(self._settings_service.get_settings().situation_endpoint, timeout=self.delay.total_seconds())
        situation_response.raise_for_status()
        situation_data = situation_response.json()

        self._position_info = PositionInfo(
            altitude_msl_m=int(meters(feet=situation_data['GPSAltitudeMSL'])),
            altitude_hae_m=int(meters(feet=situation_data['GPSHeightAboveEllipsoid'])),
            satellites=situation_data['GPSSatellites']
        )

        new_position = GPS(
            lat=situation_data['GPSLatitude'],
            lng=situation_data['GPSLongitude']
        )

        if not new_position.is_valid:
            logger.debug('Reported position is not valid')
            return

        if self._current_position is None:
            self._sound_service.play_beep(Beeps.info)

        self._current_position = new_position
        logger.debug(f'Current position: {self._current_position}')
        logger.debug(f'Position info: {self._position_info}')

    def get_current_position(self) -> GPS:
        if self._current_position is None or not self._current_position.is_valid:
            return self._settings_service.get_settings().default_position
        return self._current_position

    def position_info(self) -> PositionInfo:
        return self._position_info
