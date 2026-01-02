from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Coordinate:
    latitude: float
    longitude: float


@dataclass
class QualityAirmeasure:
    location: str
    parameter: str
    value: float
    unit: str
    measure_at: datetime
    coordinates: Optional[Coordinate] = None
    country: Optional[str] = None
    city: Optional[str] = None

    def is_valid(self) -> bool:
        if self.value < 0 :
            return False
        if self.parameter not in ['pm25', 'pm10', 'co2', 'o3', 'no2']:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            'location': self.location,
            'parameter': self.parameter,
            'value': self.value,
            'unit': self.unit,
            'measured_at': self.measured_at,
            'latitude': self.coordinates.latitude if self.coordinates else None,
            'longitude': self.coordinates.longitude if self.coordinates else None,
            'country': self.country,
            'city': self.city
        }
