import abc
import datetime
import logging
import time
from typing import NamedTuple
import geopy.distance
from geographiclib.geodesic import Geodesic

logger = logging.getLogger(__name__)


class GPS(NamedTuple):
    lat: float
    lng: float

    @property
    def is_valid(self) -> bool:
        return self.lat != 0 and self.lng != 0

    def __sub__(self, other: 'GPS') -> float:
        assert isinstance(other, self.__class__)  # I know, assertions are bad. Cant help myself though
        return self.distance(other)

    def distance(self, other: 'GPS') -> float:
        return geopy.distance.geodesic(tuple(self), tuple(other)).meters

    def angle(self, other: 'GPS') -> float:
        result = Geodesic.WGS84.Inverse(self.lat, self.lng, other.lat, other.lng)
        azi1 = result['azi1']
        if azi1 < 0:
            azi1 += 360
        return azi1


class ServiceWorker(metaclass=abc.ABCMeta):
    """
    Service worker provides a scafoolding for user logic to be ran every `delay` seconds.
    Tracks heartbeat and supports graceful shutdown.
    """

    delay: datetime.timedelta = datetime.timedelta(seconds=5)

    def __init__(self):
        self._heartbeat = datetime.datetime.utcnow().replace(year=1970)  # very old heartbeat as default
        self._shutdown = False

    def run(self):
        """
        Run the loop
        """
        while not self._shutdown:
            try:
                self.trigger()
                self._heartbeat = datetime.datetime.utcnow()  # Update heartbeat only if trigger executed successfully
            except:
                logger.exception(f'Unhandled error in {self.__class__.__name__}.trigger')

            time.sleep(self.delay.seconds)

    def shutdown(self):
        """
        Set shutdown flag
        """
        self._shutdown = True

    @property
    def heartbeat(self) -> datetime.datetime:
        """
        Return timestamp of last heartbeat
        """
        return self._heartbeat

    def trigger(self):
        """
        User code runs here
        """
        raise NotImplementedError()


def truncate_number(n: int) -> int:
    """
    68 -> 60
    127 -> 120
    4567 -> 4500
    12566 -> 12000
    """
    s = list(str(n))

    t = len(s)

    if t == 1:
        return n
    if t == 2:
        t = 1
    else:
        t -= 1

    for i in range(1, t):
        s[-i] = 0

    return int(''.join(map(str, s)))
