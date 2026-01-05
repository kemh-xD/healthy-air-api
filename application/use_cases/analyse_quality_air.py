import pandas as pd
from datetime import datetime
from typing import List, Dict

from application.interfaces import data_repository
from application.interfaces.data_repository import DataRepository


class AnalyzeQualityAir:

    def __init__(self, data_repository: DataRepository):

        self.data_repository = data_repository
        print("AnalyzeQualityAir initialisé avec le repository")

    async def get_dataFrame(
            self,
            country: str = None,
            days: int = 7,
            limit: int = 1000
    ) -> pd.DataFrame:
        print(f"recuperation des data")
        if country:
            print(f"pays: {country}")
        print(f"limite: {limit} mesures")

        measurements = await self.data_repository.get_latest_measurements(
            country=country,
            limit=limit
        )

        print(f"recuperation des measurements{len(measurements)}")

        data_list = []
        for measure in measurements:
            data_list.append({
                'timestamp': measure.measured_at,
                'location': measure.location,
                'city': measure.city,
                'country': measure.country,
                'parameter': measure.parameter,
                'value': measure.value,
                'unit': measure.unit,
                'latitude': measure.coordinates.latitude if measure.coordinates else None,
                'longitude': measure.coordinates.longitude if measure.coordinates else None,
            })
        if not data_list:
            print(f"aucune data found")
            return pd.DataFrame()

        df = pd.DataFrame(data_list)

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        return df

    async def get_dataframe_by_parameter(
            self,
            parameter: str,
            country: str = None,
            days: int = 7,
            limit: int = 1000
    ) -> pd.DataFrame:

        df = await self.get_dataFrame(
            country=country,
            days=days,
            limit=limit
        )
        if df.empty:
            return df

        df_filtered = df[df['parameter'] == parameter].copy()

        return df_filtered

    async def calculate_statistics(
            self,
            parameter: str,
            country: str = None,
            days: int = 7
    ) -> Dict:

        df = await self.get_dataframe_by_parameter(
            parameter=parameter,
            country=country,
            days=days
        )

        if df.empty:
            return {"error": "Aucune data disponible"}

        stats = {
            'parameter': parameter,
            'nombre_mesures': len(df),
            'moyenne': round(df['value'].mean(), 2),
            'minimum': round(df['value'].min(), 2),
            'maximum': round(df['value'].max(), 2),
            'ecart_type': round(df['value'].std(), 2),
            'mediane': round(df['value'].median(), 2),
            'unite': df['unit'].iloc[0] if 'unit' in df.columns else None
        }

        return stats

    async def analyze_trend(
            self,
            parameter: str,
            country: str = None,
            days: int = 7
    ) -> Dict:

        df = await self.get_dataframe_by_parameter(
            parameter=parameter,
            country=country,
            days=days
        )

        if df.empty or len(df) < 2 :
            return {"error": "Pas assez de data pour analyze"}

        first_value = df['value'].iloc[0]
        last_value = df['value'].iloc[-1]
        difference = last_value - first_value
        percentage_change = (difference / first_value * 100) if first_value != 0 else 0

        #determiner la trend
        if percentage_change > 5:
            trend = "Augmentation"
        elif percentage_change < -5:
            trend = "Diminution"
        else:
            trend = "Stable"

        result = {
            'parameter': parameter,
            'tendance': trend,
            'variation_pourcent': round(percentage_change, 2),
            'valeur_initiale': round(first_value, 2),
            'valeur_finale': round(last_value, 2),
            'difference': round(difference, 2),
            'date_debut': df['timestamp'].iloc[0].isoformat(),
            'date_fin': df['timestamp'].iloc[-1].isoformat()
        }

        return result

    async def analyze_peaks(
            self,
            parameter: str,
            threshold: float,
            country: str = None,
            days: int = 7
    ) -> list[Dict]:

        df = await self.get_dataframe_by_parameter(
            parameter=parameter,
            country=country,
            days=days
        )

        if df.empty:
            return []

        #flitrer les values au dessus du seuil que moi mm j'ai mis
        peaks = df[df['value'] > threshold].copy()

        #convertir en list
        peaks_list = []
        for _, row in peaks.iterrows():
            peaks_list.append({
                'timestamp': row['timestamp'].isoformat(),
                'location': row['location'],
                'city': row['city'],
                'value': round(row['value'], 2),
                'unit': row['unit'],
                'depassement': round(row['value'] - threshold, 2)
            })

        return peaks_list
