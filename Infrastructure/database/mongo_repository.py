from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
from datetime import datetime
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, BulkWriteError

from Domain.Entities import QualityAirmeasure, Coordinate
from application.interfaces.data_repository import DataRepository


class MongoRepository(DataRepository):
    """Implémentation MongoDB pour le stockage des mesures de qualité de l'air"""
    
    def __init__(self, mongo_uri: str, database_name: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[database_name]
        self.collection = self.db.air_quality_measurements
    
    async def save_measurements(self, measurements: List[QualityAirmeasure]) -> int:
        """Sauvegarde les mesures avec gestion des doublons"""
        if not measurements:
            return 0
        
        documents = [self._to_document(m) for m in measurements]
        
        # InsertMany avec ordered=False pour continuer même si doublons
        try:
            result = await self.collection.insert_many(documents, ordered=False)
            return len(result.inserted_ids)
        except BulkWriteError as e:
            # Retourner le nombre de documents effectivement insérés
            inserted_count = e.details.get('nInserted', 0)
            print(f"{len(documents) - inserted_count} mesures dupliquées ignorées")
            return inserted_count
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {e}")
            return 0
    
    async def get_measurements_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        country: Optional[str] = None
    ) -> List[QualityAirmeasure]:
        """Récupère les mesures sur une période donnée"""
        query = {
            "measured_at": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        if country:
            query["country"] = country
        
        cursor = self.collection.find(query).sort("measured_at", DESCENDING)
        documents = await cursor.to_list(length=None)
        return [self._from_document(doc) for doc in documents]
    
    async def get_latest_measurements(
        self, 
        country: Optional[str] = None, 
        limit: int = 100
    ) -> List[QualityAirmeasure]:
        """Récupère les dernières mesures"""
        query = {}
        if country:
            query["country"] = country
        
        cursor = self.collection.find(query).sort("measured_at", DESCENDING).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._from_document(doc) for doc in documents]
    
    def _to_document(self, measurement: QualityAirmeasure) -> dict:
        """Convertit une entité en document MongoDB"""
        doc = {
            "location": measurement.location,
            "parameter": measurement.parameter,
            "value": measurement.value,
            "unit": measurement.unit,
            "measured_at": measurement.measured_at,
            "country": measurement.country,
            "city": measurement.city
        }
        
        # Ajouter les coordonnées géographiques au format GeoJSON
        if measurement.coordinates:
            doc["location_geo"] = {
                "type": "Point",
                "coordinates": [
                    measurement.coordinates.longitude,
                    measurement.coordinates.latitude
                ]
            }
            doc["latitude"] = measurement.coordinates.latitude
            doc["longitude"] = measurement.coordinates.longitude
        
        return doc
    
    def _from_document(self, doc: dict) -> QualityAirmeasure:
        """Convertit un document MongoDB en entité"""
        coords = None
        if "location_geo" in doc:
            coords = Coordinate(
                latitude=doc["location_geo"]["coordinates"][1],
                longitude=doc["location_geo"]["coordinates"][0]
            )
        elif "latitude" in doc and "longitude" in doc:
            coords = Coordinate(
                latitude=doc["latitude"],
                longitude=doc["longitude"]
            )
        
        return QualityAirmeasure(
            location=doc["location"],
            parameter=doc["parameter"],
            value=doc["value"],
            unit=doc["unit"],
            measured_at=doc["measured_at"],
            coordinates=coords,
            country=doc.get("country"),
            city=doc.get("city")
        )
    
    async def create_indexes(self):
        """Créer les index pour optimiser les performances"""
        # Index sur la date (pour les requêtes temporelles)
        await self.collection.create_index([("measured_at", DESCENDING)])
        
        # Index composé pour filtrer par pays et paramètre
        await self.collection.create_index([("country", ASCENDING), ("parameter", ASCENDING)])
        
        # Index géospatial pour les requêtes par localisation
        await self.collection.create_index([("location_geo", "2dsphere")])
        
        # Index unique pour éviter les doublons exacts
        await self.collection.create_index(
            [
                ("location", ASCENDING),
                ("parameter", ASCENDING),
                ("measured_at", ASCENDING)
            ],
            unique=True
        )
        
        print("✓ Index MongoDB créés avec succès")
    
    async def get_statistics(self, country: Optional[str] = None) -> dict:
        """Récupère des statistiques sur les données stockées"""
        match_stage = {}
        if country:
            match_stage = {"$match": {"country": country}}
        
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$parameter",
                    "count": {"$sum": 1},
                    "avg_value": {"$avg": "$value"},
                    "min_value": {"$min": "$value"},
                    "max_value": {"$max": "$value"}
                }
            }
        ])
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        return {
            "total_documents": await self.collection.count_documents(match_stage if match_stage else {}),
            "by_parameter": results
        }
