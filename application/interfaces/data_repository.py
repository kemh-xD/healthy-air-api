from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from Domain.Entities import QualityAirmeasure


class DataRepository(ABC):
    """Interface pour le stockage des mesures de qualité de l'air"""
    
    @abstractmethod
    async def save_measurements(self, measurements: List[QualityAirmeasure]) -> int:
        """Sauvegarde les mesures et retourne le nombre enregistré"""
        pass
    
    @abstractmethod
    async def get_measurements_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        country: Optional[str] = None
    ) -> List[QualityAirmeasure]:
        """Récupère les mesures par période"""
        pass
    
    @abstractmethod
    async def get_latest_measurements(
        self, 
        country: Optional[str] = None, 
        limit: int = 100
    ) -> List[QualityAirmeasure]:
        """Récupère les dernières mesures"""
        pass