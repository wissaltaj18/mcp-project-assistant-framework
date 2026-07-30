"""Implémentation concrète d'EmbeddingProviderPort utilisant l'API Gemini."""

from typing import List

from google import genai

from core.ports.embedding_provider_port import EmbeddingProviderPort


class GeminiEmbeddingProvider(EmbeddingProviderPort):
    """Transforme du texte en vecteur via le modèle d'embeddings de Gemini."""

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001"):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def embed(self, text: str) -> List[float]:
        reponse = self._client.models.embed_content(model=self._model_name, contents=text)
        return list(reponse.embeddings[0].values)