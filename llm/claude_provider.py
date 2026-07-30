"""
Implémentation simple de LLMProviderPort pour Claude : un prompt, une
réponse texte -- utilisée pour les appels LLM ad-hoc (modify_function,
modify_frontend_file), séparée de ClaudeChatAgent qui gère, lui, la
conversation complète avec tool calling.
"""

import anthropic

from core.ports.llm_provider_port import LLMProviderPort


class ClaudeProvider(LLMProviderPort):
    """Parle à l'API Claude (Anthropic) pour une génération simple, sans conversation."""

    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-5"):
        self._api_key = api_key
        self._model_name = model_name
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        if self._client is None:
            raise ConnectionError(
                "Clé API Claude manquante. Configure ANTHROPIC_API_KEY dans ton terminal."
            )
        reponse = self._client.messages.create(
            model=self._model_name,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(bloc.text for bloc in reponse.content if bloc.type == "text")

    def is_available(self) -> bool:
        return bool(self._api_key)