from fastapi import FastAPI

from Presentation.api.routes import router
from Infrastructure.database.mongo_repository import MongoRepository
from Infrastructure.config.settings import settings

app = FastAPI(
    title="Air Quality Collector API",
    description="API pour collecter les données de qualité de l'air",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialise MongoDB au démarrage de l'application"""
    print("🚀 Démarrage de l'application...")
    try:
        repository = MongoRepository(
            mongo_uri=settings.MONGO_URI,
            database_name=settings.MONGO_DATABASE
        )
        await repository.create_indexes()
        print("✓ MongoDB initialisé avec succès")
    except Exception as e:
        print(f"⚠️ Avertissement MongoDB: {e}")


@app.get("/")
async def root():
    return{"message" : "Hello Health-air-api"}


app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}