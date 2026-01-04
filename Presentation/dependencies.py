from functools import lru_cache

from fastapi import Depends

from application.use_cases.analyse_quality_air import AnalyzeQualityAir
from application.use_cases.collect_quality_air import CollectQualityAir
from Infrastructure.external.openaq_client import OpenAQClient
from Infrastructure.database.mongo_repository import MongoRepository
from Infrastructure.config.settings import settings


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