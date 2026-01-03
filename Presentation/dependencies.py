from functools import lru_cache

from fastapi import Depends

from application.use_cases.collect_quality_air import CollectQualityAir
from Infrastructure.external.openaq_client import OpenAQClient
from Infrastructure.config.settings import settings


@lru_cache()
def get_openaq_client() -> OpenAQClient:
    """Factory pour le client OpenAQ"""
    return OpenAQClient(api_key=settings.OPENAQ_API_KEY)


def get_collect_use_case(
        client: OpenAQClient = Depends(get_openaq_client)
) -> CollectQualityAir:
    """implementer pour le reste mongo et autre"""
    return CollectQualityAir(
        data_source=client,
        repository=None  # À remplacer par ton collègue
    )