"""
Port pour LIRE des Resources (fichiers .md). Séparé de l'écriture
(resource_writer_port.py) selon le principe Interface Segregation --
la plupart des consommateurs n'ont besoin que de lire, pas d'écrire.
"""

from abc import ABC, abstractmethod
from typing import List


class ResourceReaderPort(ABC):
    """Contrat pour tout composant capable de lire des Resources d'un projet."""

    @abstractmethod
    def read(self, project_name: str, resource_name: str) -> str:
        """
        Lit le contenu d'une Resource précise.

        Args:
            project_name: Le nom du projet (ex: "aegisai")
            resource_name: Le nom du fichier (ex: "business_rules.md")

        Returns:
            Le contenu texte de la Resource

        Raises:
            FileNotFoundError: si la Resource n'existe pas
        """
        raise NotImplementedError

    @abstractmethod
    def list_available(self, project_name: str) -> List[str]:
        """Liste les noms de toutes les Resources disponibles pour un projet."""
        raise NotImplementedError