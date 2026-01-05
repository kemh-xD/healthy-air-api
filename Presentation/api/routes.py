from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd

from Presentation.api.schemas import (
    CollectionRequest,
    CollectionResponse,
    MeasurementSchema, ChatRequest
)
from Presentation.dependencies import get_collect_use_case, get_mongo_repository, get_analyze_use_case, \
    get_predict_use_case, get_chatbot_use_case
from application.use_cases.analyse_quality_air import AnalyzeQualityAir
from application.use_cases.chatbot_quality_air import ChatbotQualityAir
from application.use_cases.collect_quality_air import CollectQualityAir
from Infrastructure.database.mongo_repository import MongoRepository
from application.use_cases.predict_quality_air import PredictQualityAir

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



@router.get("/analysis/statistics")
async def get_analysis_statistics(
        parameter: str = Query(..., description="Paramètre à analyser (pm25, pm10, co, etc.)"),
        country: str = Query(None, description="Code pays (ex: TG)"),
        days: int = Query(7, ge=1, le=30, description="Nombre de jours"),
        analyzer: AnalyzeQualityAir = Depends(get_analyze_use_case)
):
    try:
        stats = await analyzer.calculate_statistics(
            parameter=parameter,
            country=country,
            days=days
        )

        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/trend")
async def get_analysis_trend(
        parameter: str = Query(..., description="Paramètre à analyser"),
        country: str = Query(None, description="Code pays"),
        days: int = Query(7, ge=1, le=30),
        analyzer: AnalyzeQualityAir = Depends(get_analyze_use_case)
):
    try:
        trend = await analyzer.analyze_trend(
            parameter=parameter,
            country=country,
            days=days
        )
        if "error" in trend:
            raise HTTPException(status_code=404, detail=trend["error"])
        return {
            "success": True,
            "data": trend
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/peaks")
async def get_analysis_peaks(
    parameter: str = Query(..., description="Paramètre à analyser"),
    threshold: float = Query(..., description="Seuil de détection"),
    country: str = Query(None, description="Code pays"),
    days: int = Query(7, ge=1, le=30),
    analyzer: AnalyzeQualityAir = Depends(get_analyze_use_case)
):
    try:

        peaks = await analyzer.identify_peaks(
            parameter=parameter,
            country=country,
            days=days,
            threshold=threshold
        )
        if "error" in peaks:
            raise HTTPException(status_code=404, detail=peaks["error"])
        return {
            "success": True,
            "count": len(peaks),
            "threshold": threshold,
            "data": peaks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("analysis/report")
async def get_analysis_report(
        parameter: str = Query(..., description="Paramètre à analyser"),
        country: str = Query(None, description="Code pays"),
        days: int = Query(7, ge=1, le=30),
        threshold: float = Query(50.0, description="Seuil pour les pics"),
        analyzer: AnalyzeQualityAir = Depends(get_analyze_use_case)
):
    try:
        stats = await analyzer.calculate_statistics(
            parameter,
            country,
            days
        )
        trend = await analyzer.analyze_trend(
            parameter,
            country,
            days
        )
        peaks = await analyzer.identify_peaks(
            parameter,
            country,
            days,
            threshold
        )

        return {
            "success": True,
            "parameter": parameter,
            "country": country,
            "period_days": days,
            "report": {
                "statistiques": stats,
                "tendance": trend,
                "pics": {
                    "count": len(peaks),
                    "threshold": threshold,
                    "list": peaks
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#routes pour les predictions
@router.post("/predict/train/linear")
async def train_linear_regression(
        parameter: str = Query(..., description="Paramètre à prédire (pm25, pm10, etc.)"),
        country: str = Query(None, description="Code pays"),
        lookback: int = Query(24, ge=1, le=168, description="Heures à regarder en arrière"),
        predictor: PredictQualityAir = Depends(get_predict_use_case)
):
    try:
        result = await predictor.train_linear_model(
            parameter=parameter,
            country=country,
            lookback=lookback
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        response = {
            "success": True,
            "model_type": result["model_type"],
            "parameter": result["parameter"],
            "metrics": result["metrics"],
            "lookback": result["lookback"]
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/train/random-forest")
async def train_random_forest(
        parameter: str = Query(..., description="Paramètre à prédire"),
        country: str = Query(None, description="Code pays"),
        lookback: int = Query(24, ge=1, le=168),
        n_estimators: int = Query(100, ge=10, le=500, description="Nombre d'arbres"),
        predictor: PredictQualityAir = Depends(get_predict_use_case)
):

    try:
        result = await predictor.train_random_forest(
            parameter=parameter,
            country=country,
            lookback=lookback,
            n_estimators=n_estimators
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        response = {
            "success": True,
            "model_type": result["model_type"],
            "parameter": result["parameter"],
            "n_estimators": result["n_estimators"],
            "metrics": result["metrics"],
            "lookback": result["lookback"]
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/train/future")
async def predict_future(
        parameter: str = Query(..., description="Paramètre à prédire"),
        country: str = Query(None, description="Code pays"),
        hours_ahead: int = Query(24, ge=1, le=168, description="Heures à prédire"),
        model_type: str = Query("random_forest", description="linear ou random_forest"),
        predictor: PredictQualityAir = Depends(get_predict_use_case)
):
    try:
        if model_type == "linear":
            model_result = await predictor.train_linear_model(parameter, country)
        else:
            model_result = await predictor.train_random_forest(parameter, country)

        if "error" in model_result:
            raise HTTPException(status_code=404, detail=model_result["error"])

        # Faire les prédictions
        predictions = await predictor.predict_future(model_result, hours_ahead)

        return {
            "success": True,
            "parameter": parameter,
            "model_type": model_result["model_type"],
            "model_metrics": model_result["metrics"],
            "predictions_count": len(predictions),
            "predictions": predictions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict/compare")
async def compare_prediction_models(
        parameter: str = Query(..., description="Paramètre à prédire"),
        country: str = Query(None, description="Code pays"),
        predictor: PredictQualityAir = Depends(get_predict_use_case)
):

    try:
        comparison = await predictor.compare_models(parameter, country)

        if "error" in comparison:
            raise HTTPException(status_code=404, detail=comparison["error"])

        return {
            "success": True,
            "comparison": comparison
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/full-pipeline")
async def full_prediction_pipeline(
        parameter: str = Query(..., description="Paramètre à prédire"),
        country: str = Query(None, description="Code pays"),
        hours_ahead: int = Query(24, ge=1, le=168),
        predictor: PredictQualityAir = Depends(get_predict_use_case)
):

    try:
        #Comparer les modèles
        comparison = await predictor.compare_models(parameter, country)

        if "error" in comparison:
            raise HTTPException(status_code=404, detail=comparison["error"])

        # Entraîner le meilleur modèle
        winner = comparison["winner"]
        if winner == "Linear Regression":
            model_result = await predictor.train_linear_model(parameter, country)
        else:
            model_result = await predictor.train_random_forest(parameter, country)

        # Faire les prédictions
        predictions = await predictor.predict_future(model_result, hours_ahead)

        return {
            "success": True,
            "parameter": parameter,
            "pipeline": {
                "models_comparison": comparison,
                "best_model": winner,
                "model_metrics": model_result["metrics"],
                "predictions_count": len(predictions),
                "predictions": predictions
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Schémas



@router.post("/chatbot/ask")
async def ask_chatbot(
        request: ChatRequest,
        chatbot: ChatbotQualityAir = Depends(get_chatbot_use_case)
):

    try:
        response = await chatbot.chat(
            user_message=request.message,
            parameter=request.parameter,
            country=request.country,
            include_context=request.include_context
        )

        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chatbot/explain-prediction")
async def explain_current_prediction(
        parameter: str = Query("pm25"),
        country: str | None = Query(None),
        chatbot: ChatbotQualityAir = Depends(get_chatbot_use_case)
):

    try:
        explanation = await chatbot.explain_prediction(parameter, country)

        if "error" in explanation:
            raise HTTPException(status_code=404, detail=explanation["error"])

        return explanation

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chatbot/reset")
async def reset_chatbot_conversation(
        chatbot: ChatbotQualityAir = Depends(get_chatbot_use_case)
):

    chatbot.reset_conversation()
    return {"success": True, "message": "Conversation réinitialisée"}


@router.get("/chatbot/history")
async def get_chatbot_history(
        chatbot: ChatbotQualityAir = Depends(get_chatbot_use_case)
):

    history = chatbot.get_conversation_history()
    return {
        "success": True,
        "conversation_length": len(history),
        "history": history
    }