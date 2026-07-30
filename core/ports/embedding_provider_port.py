"""Port pour transformer du texte en vecteur numérique (embedding)."""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProviderPort(ABC):
    """Contrat pour tout fournisseur capable de transformer du texte en vecteur."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Renvoie le vecteur d'embedding représentant le sens du texte donné."""
        raise NotImplementedError