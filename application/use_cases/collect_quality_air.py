import pandas as pd
from typing import Optional, List

from Domain.Entities import QualityAirmeasure
from Domain.exceptions import DataSourceError
from application.interfaces.data_repository import DataRepository
from application.interfaces.data_source import DataSource


class CollectQualityAir:
    def __init__(
            self,
            data_source: DataSource,
            repository: Optional[DataRepository] = None
    ):
        self.data_source = data_source
        self.repository = repository

    async def execute(
            self,
            country: str = "TG",
            parameters: List[str] = None,
            save_to_storage: bool = True
    ) -> pd.DataFrame:
        "collecter des datas et retourner un datafame panda"
        try:
            "recuperer les data"
            measurments = await self.data_source.fetch_latest_measurements(
                country=country,
                parameters=parameters or ["pm25", "pm10"],
                limit = 1000
            )

            "valider les data"
            valid_measurements = self.validate_measurements(
                measurments
            )

            "Sauvegarder les data"
            if save_to_storage and self.repository:
                saved_count = await self.repositpry.save_measurements(valid_measurements)
                print(f"✓ {saved_count} mesures sauvegardees")

                "conversion en dataframe"
                df = self._to_dataframe(valid_measurements)

                "nettoyage et enrichissements pour mon panda"
                df = self._clean_dataframe(df)
                return df
        except Exception as e:
            raise DataSourceError(f"Erreur lors de la collecte: {str(e)}")

    def _validate_measurements(
            self,
            measurements: List[QualityAirmeasure]
    ) -> List[QualityAirmeasure]:

        "Filtre les mesures invalides"
        valid = [m for m in measurements if m.is_valid()]
        invalid_count = len(measurements) - len(valid)

        if invalid_count > 0:
            print(f"{invalid_count} mesures invalides ignorees")

        return valid

    def _to_dataframe(
            self,
            measurements: List[QualityAirmeasure]
    ) -> pd.DataFrame:
        "Conversions des entities en DataFrame pandas"
        data = [m.to_dict() for m in measurements]
        return pd.DataFrame(data)

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:

        # Conversion du timestamp en index datetime
        df['measured_at'] = pd.to_datetime(df['measured_at'])
        df = df.set_index('measured_at')

        # Tri chronologique
        df = df.sort_index()

        # Suppression des doublons
        df = df.drop_duplicates(subset=['location', 'parameter'], keep='last')

        # Gestion des valeurs manquantes
        df = df.dropna(subset=['value'])

        return df



