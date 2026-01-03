"""
Générateur de données de test pour OpenAQ
"""
from datetime import datetime, timedelta
import random
from Domain.Entities import QualityAirmeasure, Coordinate


class MockOpenAQGenerator:
    """Génère des données de test réalistes pour l'API OpenAQ"""
    
    def __init__(self):
        self.locations = [
            ("Lomé Centre", 6.1319, 1.2223),
            ("Sokodé", 8.9833, 1.1333),
            ("Kara", 9.5511, 1.1914),
            ("Atakpamé", 7.5333, 1.1167),
            ("Bassar", 9.2667, 0.7833),
        ]
        
        self.parameter_ranges = {
            "pm25": (5.0, 250.0),
            "pm10": (10.0, 300.0),
            "o3": (0.0, 100.0),
            "no2": (0.0, 80.0),
            "so2": (0.0, 50.0),
            "co": (0.0, 5.0),
        }
    
    def generate_measurements(
        self,
        parameters: list[str],
        count: int = 10
    ) -> list[QualityAirmeasure]:
        """Génère des mesures aléatoires"""
        measurements = []
        
        for _ in range(count):
            location_name, lat, lon = random.choice(self.locations)
            parameter = random.choice(parameters)
            
            min_val, max_val = self.parameter_ranges.get(parameter, (0.0, 100.0))
            value = round(random.uniform(min_val, max_val), 2)
            
            # Date aléatoire dans les dernières 24h
            hours_ago = random.randint(0, 24)
            measured_at = datetime.now() - timedelta(hours=hours_ago)
            
            measurement = QualityAirmeasure(
                location=location_name,
                parameter=parameter,
                value=value,
                unit="µg/m³",
                measured_at=measured_at,
                country="TG",
                city=location_name,
                coordinates=Coordinate(latitude=lat, longitude=lon),
                source_name="Mock OpenAQ API"
            )
            
            measurements.append(measurement)
        
        return measurements
