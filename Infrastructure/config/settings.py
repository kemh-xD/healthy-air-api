from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    OPENAQ_API_KEY: str = ""
    OPENAQ_DEFALUT_COUNTRY: str = "TG"

    COLLECTION_INTERVAL_MINUTES: int = 30
    DEFAULT_PARAMETERS: list = ["pm25", "pm10"]

    class Config:
        env_file = ".env"

settings = Settings()