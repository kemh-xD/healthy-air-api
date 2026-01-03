from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd

from Presentation.api.schemas import (
    CollectionRequest,
    CollectionResponse,
    MeasurementSchema
)
from Presentation.dependencies import get_collect_use_case, get_mongo_repository
from application.use_cases.collect_quality_air import CollectQualityAir
from Infrastructure.database.mongo_repository import MongoRepository

router = APIRouter(tags=["collection"])


@router.post("/collect", response_model=CollectionResponse)
async def collect_air_quality(
        request: CollectionRequest,
        use_case: CollectQualityAir = Depends(get_collect_use_case)
):
    """
    Endpoint pour déclencher la collecte.
    Retourne un résumé + les données en JSON pour vérification.
    """
    try:
        df = await use_case.execute(
            country=request.country,
            parameters=request.parameters,
            save_to_storage=request.save_to_storage
        )

        # Statistiques du DataFrame
        stats = {
            "total_measurements": len(df),
            "parameters": df['parameter'].unique().tolist(),
            "locations": df['location'].unique().tolist(),
            "date_range": {
                "start": df.index.min().isoformat(),
                "end": df.index.max().isoformat()
            }
        }

        # Conversion d'un échantillon en JSON
        sample = df.head(10).reset_index().to_dict(orient='records')

        return CollectionResponse(
            success=True,
            message=f"Collecte réussie: {len(df)} mesures",
            statistics=stats,
            sample_data=sample
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collect/preview")
async def preview_collection(
        country: str = "TG",
        parameters: Optional[List[str]] = None,
        use_case: CollectQualityAir = Depends(get_collect_use_case)
):
    """
    Prévisualise les données sans les sauvegarder.
    Utile pour tester.
    """
    df = await use_case.execute(
        country=country,
        parameters=parameters or ["pm25", "pm10"],
        save_to_storage=False
    )

    return {
        "preview": df.head(20).reset_index().to_dict(orient='records'),
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": df.columns.tolist()
    }


@router.get("/storage/stats")
async def get_storage_statistics(
        country: Optional[str] = None,
        repository: MongoRepository = Depends(get_mongo_repository)
):
    """
    Récupère les statistiques sur les données stockées dans MongoDB
    """
    try:
        stats = await repository.get_statistics(country=country)
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/latest")
async def get_latest_stored_measurements(
        country: Optional[str] = None,
        limit: int = 50,
        repository: MongoRepository = Depends(get_mongo_repository)
):
    """
    Récupère les dernières mesures stockées dans MongoDB
    """
    try:
        measurements = await repository.get_latest_measurements(country=country, limit=limit)
        
        # Convertir en dict pour la réponse
        data = [m.to_dict() for m in measurements]
        
        return {
            "success": True,
            "count": len(data),
            "measurements": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))