"""Port pour une base vectorielle : stocke des vecteurs, retrouve les plus proches."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class VectorStorePort(ABC):
    """Contrat pour tout composant capable de stocker/rechercher des vecteurs."""

    @abstractmethod
    def upsert(self, chunk_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """Ajoute ou remplace un vecteur, avec ses métadonnées (ex: le code source, le fichier)."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, chunk_id: str) -> None:
        """Supprime un vecteur de l'index (ex: fichier source supprimé/modifié)."""
        raise NotImplementedError

    @abstractmethod
    def delete_by_file(self, file_path: str) -> None:
        """Supprime tous les vecteurs associés à un fichier donné."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Renvoie les top_k vecteurs les plus proches : (chunk_id, score, métadonnées)."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Nombre de vecteurs actuellement indexés."""
        raise NotImplementedError