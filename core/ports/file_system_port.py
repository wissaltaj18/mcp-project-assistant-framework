"""
Port pour manipuler le système de fichiers (créer/lire/supprimer des
fichiers dans generated_projects/). Séparé du reste car c'est un détail
d'infrastructure -- demain, on pourrait écrire dans un cloud storage
au lieu du disque local, sans toucher au reste du framework.
"""

from abc import ABC, abstractmethod


class FileSystemPort(ABC):
    """Contrat pour toute opération de fichiers utilisée par le framework."""

    @abstractmethod
    def create_file(self, path: str, content: str) -> None:
        """Crée un fichier avec le contenu donné (crée les dossiers parents si besoin)."""
        raise NotImplementedError

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Lit le contenu d'un fichier existant."""
        raise NotImplementedError

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Vérifie qu'un fichier existe déjà."""
        raise NotImplementedError