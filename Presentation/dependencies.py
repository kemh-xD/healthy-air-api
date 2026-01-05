from functools import lru_cache

from fastapi import Depends

from application.use_cases.analyse_quality_air import AnalyzeQualityAir
from application.use_cases.chatbot_quality_air import ChatbotQualityAir
from application.use_cases.collect_quality_air import CollectQualityAir
from Infrastructure.external.openaq_client import OpenAQClient
from Infrastructure.database.mongo_repository import MongoRepository
from Infrastructure.config.settings import settings
from application.use_cases.predict_quality_air import PredictQualityAir


@lru_cache()
def get_openaq_client() -> OpenAQClient:
    """Factory pour le client OpenAQ"""
    return OpenAQClient(api_key=settings.OPENAQ_API_KEY)


@lru_cache()
def get_mongo_repository() -> MongoRepository:
    """Factory pour le repository MongoDB"""
    return MongoRepository(
        mongo_uri=settings.MONGO_URI,
        database_name=settings.MONGO_DATABASE
    )


def get_collect_use_case(
        client: OpenAQClient = Depends(get_openaq_client),
        repository: MongoRepository = Depends(get_mongo_repository)
) -> CollectQualityAir:
    """Use case pour la collecte avec stockage MongoDB"""
    return CollectQualityAir(
        data_source=client,
        repository=repository
    )

def get_analyze_use_case() -> AnalyzeQualityAir:
    """Use case pour la analyse stockage MongoDB"""
    repository = get_mongo_repository()
    return AnalyzeQualityAir(data_repository=repository)

def get_predict_use_case() -> PredictQualityAir:
    """Use case pour la predict stockage MongoDB"""
    repository = get_mongo_repository()
    return PredictQualityAir(data_repository=repository)

_chatbot_instance = None

def get_chatbot_use_case() -> ChatbotQualityAir:
    """
    Retourne une instance du chatbot (singleton pour conserver l'historique)
    """
    global _chatbot_instance

    if _chatbot_instance is None:
        repository = get_mongo_repository()

        # Récupérer la configuration selon le provider
        provider = settings.CHATBOT_PROVIDER

        if provider == "groq":
            api_key = settings.GROQ_API_KEY if hasattr(settings, 'GROQ_API_KEY') else ""
        elif provider == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY if hasattr(settings, 'ANTHROPIC_API_KEY') else ""
        elif provider == "openai":
            api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else ""
        else:
            api_key = ""

        if not api_key:
            print(f"{provider.upper()}_API_KEY non configurée")

        _chatbot_instance = ChatbotQualityAir(
            data_repository=repository,
            api_key=api_key,
            provider=provider
        )

    return _chatbot_instance