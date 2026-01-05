

import json
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from application.interfaces.data_repository import DataRepository
from application.use_cases.analyse_quality_air import AnalyzeQualityAir

from application.use_cases.predict_quality_air import PredictQualityAir


class ChatbotQualityAir:

    def __init__(
            self,
            data_repository: DataRepository,
            api_key: str,
            provider: str = "groq"
    ):

        self.data_repository = data_repository
        self.api_key = api_key
        self.provider = provider
        self.analyzer = AnalyzeQualityAir(data_repository)
        self.predictor = PredictQualityAir(data_repository)

        # Configuration selon le provider
        if provider == "groq":
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model = "llama-3.3-70b-versatile"
            print("Chatbot initialisé avec Groq ")


        # Historique de conversation
        self.conversation_history: List[Dict] = []

    async def get_context_data(
            self,
            parameter: str = "pm25",
            country: str = "TG"
    ) -> Dict:
        """Récupère les données contextuelles"""
        try:
            stats = await self.analyzer.calculate_statistics(parameter, country)
            trend = await self.analyzer.analyze_trend(parameter, country)

            model_result = await self.predictor.train_linear_model(parameter, country)
            predictions = []
            if "error" not in model_result:
                predictions = await self.predictor.predict_future(model_result, hours_ahead=6)

            context = {
                "current_statistics": stats if "error" not in stats else None,
                "trend": trend if "error" not in trend else None,
                "predictions_6h": predictions[:6] if predictions else []
            }

            return context

        except Exception as e:
            print(f"Erreur contexte: {e}")
            return {}

    def build_system_prompt(self, context_data: Dict) -> str:
        """Construit le prompt système avec contexte"""

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        system_prompt = f"""Tu es un assistant expert en qualité de l'air au Togo.

TON RÔLE :
- Expliquer les données de pollution de manière simple
- Donner des conseils de santé personnalisés
- Expliquer les prédictions et tendances
- Être pédagogue et accessible

DONNÉES ACTUELLES ({current_time}) :
"""

        if context_data.get("current_statistics"):
            stats = context_data["current_statistics"]
            system_prompt += f"""
Statistiques PM2.5 :
- Moyenne : {stats.get('moyenne')} µg/m³
- Min/Max : {stats.get('minimum')} - {stats.get('maximum')} µg/m³
"""

        if context_data.get("trend"):
            trend = context_data["trend"]
            system_prompt += f"""
Tendance : {trend.get('tendance')} ({trend.get('variation_pourcent')}%)
De {trend.get('valeur_initiale')} à {trend.get('valeur_finale')} µg/m³
"""

        if context_data.get("predictions_6h"):
            system_prompt += "\nPrédictions 6h :\n"
            for pred in context_data["predictions_6h"][:3]:
                system_prompt += f"- +{pred['hours_ahead']}h : {pred['predicted_value']} µg/m³\n"

        system_prompt += """

NIVEAUX PM2.5 :
- Bon : 0-12 µg/m³ (Vert) 
- Modéré : 12-35 µg/m³ (Jaune) 
- Mauvais : 35-55 µg/m³ (Orange) 
- Très mauvais : 55-150 µg/m³ (Rouge) 
- Dangereux : >150 µg/m³ (Violet) 

CONSEILS :
- Bon/Modéré : Activités normales
- Orange : Limiter sport intense (personnes sensibles)
- Rouge/Violet : Éviter activités extérieures
- Dangereux : Rester à l'intérieur

TON STYLE :
- Clair et pédagogique
- Utilise des emojis
- Cite les chiffres actuels
- Donne des conseils pratiques
"""

        return system_prompt

    async def call_groq_api(self, system_prompt: str, messages: List[Dict]) -> Dict:
        """Appel API Groq """

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Format OpenAI-compatible pour Groq
            formatted_messages = [
                                     {"role": "system", "content": system_prompt}
                                 ] + messages

            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
            )

            if response.status_code != 200:
                return {
                    "error": f"Erreur API: {response.status_code}",
                    "detail": response.text
                }

            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"]
            }

    async def chat(
            self,
            user_message: str,
            parameter: str = "pm25",
            country: str = "TG",
            include_context: bool = True
    ) -> Dict:


        print(f"\nQuestion : {user_message}")

        # Récupérer le contexte
        context_data = {}
        if include_context:
            print("Récupération du contexte...")
            context_data = await self.get_context_data(parameter, country)

        # Construire le prompt système
        system_prompt = self.build_system_prompt(context_data)

        # Ajouter à l'historique
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        try:
            print(f"Appel API {self.provider.upper()}...")

            # Appeler l'API selon le provider
            if self.provider == "groq":
                api_result = await self.call_groq_api(system_prompt, self.conversation_history)
            elif self.provider == "anthropic":
                api_result = await self.call_anthropic_api(system_prompt, self.conversation_history)
            else:
                return {"error": f"Provider {self.provider} non supporté"}

            if "error" in api_result:
                return api_result

            assistant_message = api_result["content"]

            # Ajouter à l'historique
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            print(f"✅ Réponse générée ({len(assistant_message)} caractères)")

            return {
                "success": True,
                "message": assistant_message,
                "context_used": context_data if include_context else None,
                "conversation_length": len(self.conversation_history),
                "model": self.model,
                "provider": self.provider
            }

        except Exception as e:
            print(f"❌ Erreur: {e}")
            return {
                "error": str(e),
                "success": False
            }

    def reset_conversation(self):
        """Réinitialise l'historique"""
        self.conversation_history = []
        print("Conversation réinitialisée")

    def get_conversation_history(self) -> List[Dict]:
        """Retourne l'historique"""
        return self.conversation_history

    async def explain_prediction(
            self,
            parameter: str = "pm25",
            country: str = "TG"
    ) -> Dict:
        """Génère une explication des prédictions"""

        print("Explication de prédiction...")

        model_result = await self.predictor.train_random_forest(parameter, country)

        if "error" in model_result:
            return {"error": "Impossible de générer une prédiction"}

        predictions = await self.predictor.predict_future(model_result, hours_ahead=24)

        question = f"""Explique-moi ces prédictions pour les 24h :

Prédictions (6 premières heures) :
{json.dumps(predictions[:6], indent=2)}

Métriques du modèle :
- R² Score : {model_result['metrics']['r2_score']}
- MAE : {model_result['metrics']['mae']}

Explique de manière simple :
1. Pourquoi ces valeurs ?
2. Fiabilité du modèle ?
3. Facteurs influençant ?
4. Conseils aux utilisateurs ?
"""

        return await self.chat(question, parameter, country, include_context=True)