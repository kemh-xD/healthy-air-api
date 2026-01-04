from pydantic.v1 import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuration de l'application chargée depuis le fichier .env"""

    # OpenAQ API Configuration
    OPENAQ_API_KEY: str = ""
    OPENAQ_DEFALUT_COUNTRY: str = "TG"

    # Collection Settings
    COLLECTION_INTERVAL_MINUTES: int = 30
    DEFAULT_PARAMETERS: str = "pm25,pm10"

    # MongoDB Configuration (chargées depuis .env)
    MONGO_URI: str
    MONGO_DATABASE: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def default_parameters_list(self) -> List[str]:
        """Retourne DEFAULT_PARAMETERS sous forme de liste"""
        return [p.strip() for p in self.DEFAULT_PARAMETERS.split(",")]

    def validate_config(self) -> bool:
        """Vérifie que la configuration est valide"""
        if not self.MONGO_URI:
            raise ValueError("MONGO_URI doit être défini dans le fichier .env")
        if not self.MONGO_DATABASE:
            raise ValueError("MONGO_DATABASE doit être défini dans le fichier .env")
        return True

settings = Settings()
settings.validate_config()