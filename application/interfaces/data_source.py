from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from Domain.Entities import QualityAirmeasure

class DataSource(ABC):

    #ajout de certaines methodes a use pour la collecte deh

    @abstractmethod
    async def fetch_latest_measurements(
            self,
            country: str = None,
            city: str = None,
            parameters: List[str] = None,
            limit: int = 100
    ) -> List[QualityAirmeasure]:
        pass

    @abstractmethod
    async def fetch_measurements_by_period(
            self,
            start_date: datetime,
            end_date: datetime,
            country: str = None,
            parameters: List[str] = None
    ) -> List[QualityAirmeasure]:
        pass
