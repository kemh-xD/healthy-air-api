from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class CollectionRequest(BaseModel):
    "Schema de requete pour la collecte"""
    country: str = Field(default="TG", description="Code pays ISO")
    parameters: Optional[List[str]] = Field(
        default=["pm25", "pm10"],
        description="Polluants à collecter"
    )
    save_to_storage: bool = Field(
        default=True,
        description="Sauvegarder dans la base"
    )

class CollectionResponse(BaseModel):
    "Schema de reponse"
    success: bool
    message: str
    statistics: Dict[str, Any]
    sample_data: List[Dict[str, Any]]

class MeasurementSchema(BaseModel):
    "Schema d'une mesure"
    location: str
    parameter: str
    value: float
    unit: str
    measured_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    parameter: str = "pm25"
    country: str = "TG"
    include_context: bool = True