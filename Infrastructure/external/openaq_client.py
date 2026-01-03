import httpx
from typing import List, Optional
from datetime import datetime

from Domain.Entities import QualityAirmeasure, Coordinate
from Domain.exceptions import DataSourceError
from application.interfaces.data_source import DataSource
from Infrastructure.external.mock_data_generator import MockOpenAQGenerator


class OpenAQClient(DataSource):

    "implementation de l'api de openaq v3 avec fallback sur données mockées"
    BASE_URL = "https://api.openaq.org/v3"

    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False):
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key
        self.use_mock = use_mock  # Désactivé par défaut, on utilise la vraie API
        self.mock_generator = MockOpenAQGenerator()
        
        # Mapping des noms de paramètres vers leurs IDs dans l'API v3
        self.parameter_ids = {
            "pm10": 1,
            "pm25": 2,
            "pm2.5": 2,
            "o3": 3,
            "no2": 4,
            "so2": 5,
            "co": 6,
            "bc": 7,
            "co2": None  # Pas disponible dans OpenAQ
        }

    async def fetch_latest_measurements(
            self,
            country: str = None,
            city: str = None,
            parameters: List[str] = None,
            limit: int = 100
    ) -> List[QualityAirmeasure]:
        """
        Récupère les dernières mesures via /parameters/{id}/latest
        """
        
        # Si use_mock est activé, utiliser les données mockées
        if self.use_mock:
            print("⚠️ Utilisation de données mockées (use_mock=True)")
            return self.mock_generator.generate_measurements(
                count=limit,
                parameters=parameters or ["pm25", "pm10"]
            )

        # Utiliser l'API réelle
        all_measurements = []
        
        # Par défaut, récupérer PM2.5 et PM10
        if not parameters:
            parameters = ["pm25", "pm10"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Pour chaque paramètre, appeler l'endpoint /parameters/{id}/latest
                for param in parameters:
                    param_id = self.parameter_ids.get(param.lower())
                    
                    if param_id is None:
                        print(f"⚠️ Paramètre '{param}' non disponible dans OpenAQ v3")
                        continue
                    
                    response = await client.get(
                        f"{self.BASE_URL}/parameters/{param_id}/latest",
                        params={"limit": limit},
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        measurements = self._parse_latest_response(data, param)
                        all_measurements.extend(measurements)
                    else:
                        print(f"⚠️ Erreur pour {param}: {response.status_code}")
            
            if not all_measurements:
                print("⚠️ Aucune donnée trouvée, utilisation de données mockées")
                return self.mock_generator.generate_measurements(
                    count=limit,
                    parameters=parameters
                )
            
            return all_measurements[:limit]  # Limiter au nombre demandé

        except httpx.HTTPError as e:
            raise DataSourceError(f"Erreur HTTP OpenAQ: {str(e)}")
        except Exception as e:
            raise DataSourceError(f"Erreur inattendue: {str(e)}")

    async def fetch_measurements_by_period(
            self,
            start_date: datetime,
            end_date: datetime,
            country: str = None,
            parameters: List[str] = None
    ) -> List[QualityAirmeasure]:
        "Recupere les mesures sur une periode"

        params = {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "limit": 10000
        }

        if country:
            params["country"] = country
        if parameters:
            params["parameter"] = ",".join(parameters)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/measurements",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    def _parse_latest_response(self, data: dict, parameter: str) -> List[QualityAirmeasure]:
        """Parse la réponse de /parameters/{id}/latest"""
        measurements = []
        
        for result in data.get("results", []):
            try:
                # Extraction des coordonnées
                coords = None
                if result.get("coordinates"):
                    coords = Coordinate(
                        latitude=result["coordinates"]["latitude"],
                        longitude=result["coordinates"]["longitude"]
                    )
                
                # Gestion du timestamp
                datetime_info = result.get("datetime", {})
                measured_at = datetime.fromisoformat(
                    datetime_info.get("utc", "").replace("Z", "+00:00")
                )
                
                # Récupérer les infos de location via l'ID si besoin
                # Pour l'instant, on utilise l'ID comme nom
                location_id = result.get("locationsId", "Unknown")
                
                # Créer l'entité
                measurement = QualityAirmeasure(
                    location=f"Location {location_id}",
                    parameter=parameter.lower(),
                    value=float(result.get("value", 0)),
                    unit="µg/m³" if parameter in ["pm25", "pm10"] else "ppm",
                    measured_at=measured_at,
                    coordinates=coords,
                    country=None,  # Non disponible dans cette réponse
                    city=None
                )
                
                measurements.append(measurement)
                
            except (KeyError, ValueError, TypeError) as e:
                print(f"Erreur parsing mesure: {e}")
                continue
        
        return measurements

    def _parse_v3_locations_response(self, data: dict) -> List[QualityAirmeasure]:
        "Parse la réponse v3 depuis l'endpoint /locations"
        measurements = []

        for location in data.get("results", []):
            try:
                # Extraction des coordonnées
                coords = None
                if location.get("coordinates"):
                    coords = Coordinate(
                        latitude=location["coordinates"]["latitude"],
                        longitude=location["coordinates"]["longitude"]
                    )

                # Parcourir les sensors de chaque location
                for sensor in location.get("sensors", []):
                    latest = sensor.get("latest")
                    if not latest or not latest.get("value"):
                        continue
                    
                    parameter_info = sensor.get("parameter", {})
                    
                    # Gestion du timestamp
                    measured_at = datetime.fromisoformat(
                        latest.get("datetime", "").replace("Z", "+00:00")
                    )

                    # Création de l'entité
                    measurement = QualityAirmeasure(
                        location=location.get("name", "Unknown"),
                        parameter=parameter_info.get("name", "").lower(),
                        value=float(latest.get("value", 0)),
                        unit=parameter_info.get("units", ""),
                        measured_at=measured_at,
                        coordinates=coords,
                        country=location.get("country", {}).get("name"),
                        city=location.get("locality")
                    )

                    measurements.append(measurement)

            except (KeyError, ValueError, TypeError) as e:
                # Log l'erreur mais continue le parsing
                print(f"Erreur parsing location: {e}")
                continue

        return measurements

    def _parse_response(self, data: dict) -> List[QualityAirmeasure]:
        "Transforme la réponse JSON en entités métier (v2 legacy)"
        measurements = []

        for result in data.get("results", []):
            try:
                # Extraction des coordonnées
                coords = None
                if result.get("coordinates"):
                    coords = Coordinate(
                        latitude=result["coordinates"]["latitude"],
                        longitude=result["coordinates"]["longitude"]
                    )

                # Gestion du timestamp
                date_obj = result.get("date", {})
                measured_at = datetime.fromisoformat(
                    date_obj.get("utc", "").replace("Z", "+00:00")
                )

                # Création de l'entité
                measurement = QualityAirmeasure(
                    location=result.get("location", "Unknown"),
                    parameter=result.get("parameter", "").lower(),
                    value=float(result.get("value", 0)),
                    unit=result.get("unit", ""),
                    measured_at=measured_at,
                    coordinates=coords,
                    country=result.get("country"),
                    city=result.get("city")
                )

                measurements.append(measurement)

            except (KeyError, ValueError, TypeError) as e:
                # Log l'erreur mais continue le parsing
                print(f"Erreur parsing mesure: {e}")
                continue

        return measurements