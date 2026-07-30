"""
Choisit quel LLMProviderPort instancier selon la configuration.
Trois choix aujourd'hui (ollama_qwen, gemini, claude) -- ajouter un
quatrième provider ne demande de modifier QUE ce fichier.
"""

import os

from core.ports.llm_provider_port import LLMProviderPort
from config.settings import FrameworkSettings
from config.llm_config import LLMConfig, GeminiConfig
from llm.ollama_qwen_provider import OllamaQwenProvider
from llm.gemini_provider import GeminiProvider
from llm.claude_provider import ClaudeProvider


def create_llm_provider(settings: FrameworkSettings, llm_config: LLMConfig) -> LLMProviderPort:
    """Instancie le provider LLM actif selon FrameworkSettings.active_llm_provider."""
    if settings.active_llm_provider == "ollama_qwen":
        return OllamaQwenProvider(llm_config)

    if settings.active_llm_provider == "gemini":
        return GeminiProvider(GeminiConfig.from_env())

    if settings.active_llm_provider == "claude":
        return ClaudeProvider(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    raise ValueError(
        f"Provider LLM inconnu : '{settings.active_llm_provider}'. "
        "Choix possibles : 'ollama_qwen', 'gemini', 'claude'."
    )