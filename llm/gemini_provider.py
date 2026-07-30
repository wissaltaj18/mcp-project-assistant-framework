"""
Implémentation concrète de LLMProviderPort pour Gemini (Google AI Studio).
Bascule possible depuis Ollama/Qwen en changeant uniquement la config --
aucune modification de core/, services/, ou agents/. C'est exactement
le Dependency Inversion Principle en action.
"""

from google import genai

from core.ports.llm_provider_port import LLMProviderPort
from config.llm_config import GeminiConfig


class GeminiProvider(LLMProviderPort):
    """Parle à l'API Gemini (cloud, gratuit avec les modèles Flash)."""

    def __init__(self, config: GeminiConfig):
        self._config = config
        self._client = genai.Client(api_key=config.api_key) if config.api_key else None

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        if self._client is None:
            raise ConnectionError(
                "Clé API Gemini manquante. Configure GEMINI_API_KEY dans ton terminal."
            )
        reponse = self._client.models.generate_content(
            model=self._config.model_name,
            contents=prompt,
        )
        return reponse.text

    def is_available(self) -> bool:
        return bool(self._config.api_key)