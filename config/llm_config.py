"""Configuration spécifique au fournisseur LLM actif."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    model_name: str
    base_url: str
    timeout_seconds: int

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            model_name=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
        )


@dataclass(frozen=True)
class GeminiConfig:
    """Configuration pour le provider Gemini (alternative à Ollama/Qwen)."""

    api_key: str
    model_name: str

    @classmethod
  
    def from_env(cls) -> "GeminiConfig":
        from config import credentials_store
        return cls(
            api_key=credentials_store.get("GEMINI_API_KEY"),
            model_name=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        )