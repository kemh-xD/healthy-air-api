"""
Script pour initialiser la base de données MongoDB
Crée les index nécessaires pour optimiser les performances
"""
import asyncio
from Infrastructure.database.mongo_repository import MongoRepository
from Infrastructure.config.settings import settings


async def init_database():
    """Initialise la base de données et crée les index"""
    print("Initialisation de MongoDB...")
    
    repository = MongoRepository(
        mongo_uri=settings.MONGO_URI,
        database_name=settings.MONGO_DATABASE
    )
    
    try:
        await repository.create_indexes()
        print("✓ Base de données initialisée avec succès")
        
        # Afficher les statistiques
        stats = await repository.get_statistics()
        print(f"\nStatistiques:")
        print(f"   - Total documents: {stats['total_documents']}")
        
    except Exception as e:
        print(f"Erreur lors de l'initialisation: {e}")
    

if __name__ == "__main__":
    asyncio.run(init_database())
