
from typing import Dict, List, Tuple

from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pandas.core.common import random_state
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

from application.interfaces.data_repository import DataRepository


class PredictQualityAir:

    def __init__(self, data_repository: DataRepository):
        self.data_repository = data_repository
        self.scaler = StandardScaler()

    async def prepare_data(
            self,
            parameter: str,
            country: str = None,
            days: int = 30,
            limit: int = 1000
    ) -> pd.DataFrame:
        measurements = await self.data_repository.get_latest_measurements(
            country=country,
            limit=limit
        )
        if not measurements:
            return pd.DataFrame()

        data_list = []
        for measure in measurements:
            if measure.parameter == parameter:
                data_list.append({
                    'timestamp': measure.measured_at,
                    'value': measure.value,
                    'location': measure.location
                })
        if not data_list:
            return pd.DataFrame()

        df = pd.DataFrame(data_list)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        #bon je regroupe les data pas heure meme
        df_hourly = df.groupby(df['timestamp'].dt.floor('H'))['value'].mean().reset_index()
        df_hourly.columns = ['timestamp', 'value']

        #creation des features temporelles
        df_hourly['hour'] = df_hourly['timestamp'].dt.hour
        df_hourly['day_of_week'] = df_hourly['timestamp'].dt.dayofweek
        df_hourly['day_of_month'] = df_hourly['timestamp'].dt.day

        return df_hourly

    #ceration de sequence pour entainer le modele on prend des heurs en arrieres pour la [rediction
    def create_sequences(
            self,
            df: pd.DataFrame,
            lookback: int = 24
    ) -> Tuple[np.ndarray, np.ndarray]:

        values = df['value'].values
        x, y = [], []

        for i in range(lookback, len(values)):
            x.append(values[i-lookback:i])
            y.append(values[i])

        x = np.array(x)
        y = np.array(y)

        return x, y


    #training d'un modele simple (linearisation)
    async def train_linear_model(
            self,
            parameter: str,
            country: str = None,
            lookback: int = 24
    ) -> Dict:

        df = await self.prepare_data(
            parameter,
            country
        )

        if df.empty:
            return {"error": "pas assez de donnees"}

        x, y = self.create_sequences(df, lookback)

        if len(x) < 50:
            return {"error": f"pas assez de donnes min 50 mais on a juste {len(x)}"}

        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state = 42
        )

        #training du modele
        model = LinearRegression()
        model.fit(x_train, y_train)

        y_pred = model.predict(x_test)

        #calcul des metriques
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        return {
            "model_type": "Linear Regression",
            "parameter": parameter,
            "metrics": {
                "r2_score": round(r2, 3),
                "mae": round(mae, 2),
                "rmse": round(np.sqrt(mse), 2)
            },
            "model": model,
            "lookback": lookback,
            #pour predire pour le future
            "last_sequence": x[-1]
        }

    #ML
    async def train_random_forest(
            self,
            parameter: str,
            country: str = None,
            lookback: int = 24,
            n_estimators: int = 100
    ) -> Dict:
        """Entraîne un modèle Random Forest"""

        df = await self.prepare_data(parameter, country)

        if df.empty:
            return {"error": "Pas assez de données"}

        x, y = self.create_sequences(df, lookback)

        if len(x) < 50:
            return {"error": f"Pas assez de données : min 50 mais on a {len(x)}"}

        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state=42
        )

        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        model.fit(x_train, y_train)

        # Prédictions
        y_pred = model.predict(x_test)

        # Métriques
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        # Feature importance
        feature_importance = model.feature_importances_
        top_features = sorted(
            enumerate(feature_importance),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        print("Top 5 features importantes:")
        for idx, importance in top_features:
            print(f"   Hour -{lookback-idx}: {importance:.3f}")

        return {
            "model_type": "Random Forest",
            "parameter": parameter,
            "n_estimators": n_estimators,
            "metrics": {
                "r2_score": round(r2, 3),
                "mae": round(mae, 2),
                "rmse": round(np.sqrt(mse), 2)
            },
            "model": model,
            "lookback": lookback,
            "last_sequence": x[-1]
        }

    #DL va nous permettre de predire pour des heures en avance
    async def predict_future(
            self,
            model_result: Dict,
            hours_ahead: int = 24
    ) -> List[Dict]:


        if "error" in model_result:
            return []

        model = model_result["model"]
        last_sequence = model_result["last_sequence"]
        lookback = model_result["lookback"]

        predictions = []
        current_sequence = last_sequence.copy()

        for i in range(hours_ahead):
            next_value = model.predict([current_sequence])[0]

            # Timestamp futur
            future_time = datetime.now() + timedelta(hours=i+1)

            predictions.append({
                "timestamp": future_time.isoformat(),
                "predicted_value": round(float(next_value), 2),
                "hours_ahead": i + 1
            })

            current_sequence = np.append(current_sequence[1:], next_value)

        print(f"{len(predictions)} prédictions générées")

        return predictions

    #comparer les 2 modeles DL et ML pour voir juste
    async def compare_models(
            self,
            parameter: str,
            country: str = None
    ) -> Dict:

        # training les deux modèles
        linear_result = await self.train_linear_model(parameter, country)
        rf_result = await self.train_random_forest(parameter, country)

        if "error" in linear_result or "error" in rf_result:
            return {"error": "Impossible de comparer les modèles"}

        # Comparer les métriques
        comparison = {
            "parameter": parameter,
            "models": {
                "Linear Regression": linear_result["metrics"],
                "Random Forest": rf_result["metrics"]
            },
            "winner": None
        }

        # Déterminer le meilleur modèle (basé sur R²)
        if linear_result["metrics"]["r2_score"] > rf_result["metrics"]["r2_score"]:
            comparison["winner"] = "Linear Regression"
        else:
            comparison["winner"] = "Random Forest"

        print(f"Meilleur modèle: {comparison['winner']}")

        return comparison





