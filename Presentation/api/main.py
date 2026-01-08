# Presentation/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from Presentation.api.routes import router
from Infrastructure.database.mongo_repository import MongoRepository
from Infrastructure.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application
    (remplace on_event qui est déprécié)
    """
    print("Démarrage de l'application...")
    try:
        repository = MongoRepository(
            mongo_uri=settings.MONGO_URI,
            database_name=settings.MONGO_DATABASE
        )
        await repository.create_indexes()
        print("MongoDB initialisé avec succès")
    except Exception as e:
        print(f"Avertissement MongoDB: {e}")

    yield
    print("Arrêt de l'application...")


app = FastAPI(
    title="Air Quality Collector API",
    description="API pour collecter et analyser les données de qualité de l'air",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS pour permettre les requêtes depuis React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React (Create React App)
        "http://localhost:5173",  # Vite
        "http://localhost:5174",  # Vite alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Autorise toutes les méthodes (GET, POST, etc.)
    allow_headers=["*"],  # Autorise tous les headers
)


@app.get("/")
async def root():
    return {
        "message": "Hello Health-air-api",
        "version": "1.0.0",
        "endpoints": {
            "collection": "/api/v1/collect",
            "analysis": "/api/v1/analysis/*",
            "storage": "/api/v1/storage/*",
            "docs": "/docs"
        }
    }



app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "healthy-air-api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)