from typing import NamedTuple
import geopy.distance


class GPS(NamedTuple):
    lat: float
    lng: float

    @property
    def is_valid(self) -> bool:
        return self.lat != 0 and self.lng != 0

    def __sub__(self, other: 'GPS') -> float:
        assert isinstance(other, self.__class__)

        return geopy.distance.geodesic(tuple(self), tuple(other)).meters
