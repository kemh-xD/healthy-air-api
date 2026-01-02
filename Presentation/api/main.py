from fastapi import FastAPI

from Presentation.api.routes import router

app = FastAPI(
    title="Air Quality Collector API",
    description="API pour collecter les données de qualité de l'air",
    version="1.0.0"
)

@app.get("/")
async def root():
    return{"message" : "Hello Health-air-api"}



app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}