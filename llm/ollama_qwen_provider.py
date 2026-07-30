"""
Implémentation concrète de LLMProviderPort pour un modèle Qwen tournant
en local via Ollama. Communique en HTTP avec l'API locale d'Ollama.
"""

import requests

from core.ports.llm_provider_port import LLMProviderPort
from config.llm_config import LLMConfig


class OllamaQwenProvider(LLMProviderPort):
    """Parle à un serveur Ollama local exposant un modèle Qwen."""

    def __init__(self, config: LLMConfig):
        self._config = config

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        url = f"{self._config.base_url}/api/generate"
        try:
            reponse = requests.post(
                url,
                json={
                    "model": self._config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=self._config.timeout_seconds,
            )
        except requests.RequestException as e:
            raise ConnectionError(
                f"Impossible de joindre Ollama à {self._config.base_url}. "
                f"Est-il bien lancé ? (ollama serve) Détail : {e}"
            )

        if reponse.status_code != 200:
            raise RuntimeError(f"Erreur Ollama (code {reponse.status_code}) : {reponse.text}")

        return reponse.json().get("response", "")

    def is_available(self) -> bool:
        try:
            reponse = requests.get(f"{self._config.base_url}/api/tags", timeout=5)
            return reponse.status_code == 200
        except requests.RequestException:
            return False