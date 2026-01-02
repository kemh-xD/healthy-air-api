import httpx
from typing import List, Optional
from datetime import datetime

from Domain.Entities import QualityAirmeasure, Coordinate
from Domain.exceptions import DataSourceError
from application.interfaces.data_source import DataSource


class OpenAQClient(DataSource):

    "implementation de l'api de openaq"
    BASE_URL = "https://api.openaq.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key

    async def fetch_latest_measurements(
            self,
            country: str = None,
            city: str = None,
            parameters: List[str] = None,
            limit: int = 100
    ) -> List[QualityAirmeasure]:
        "Récupere les dernieres mesures depuis OpenAQ"

        params = {
            "limit": limit,
            "order_by": "datetime",
            "sort": "desc"
        }

        if country:
            params["country"] = country
        if city:
            params["city"] = city
        if parameters:
            params["parameter"] = ",".join(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/latest",
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

            return self._parse_response(data)

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

    def _parse_response(self, data: dict) -> List[QualityAirmeasure]:
        "Transforme la réponse JSON en entités métier"
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