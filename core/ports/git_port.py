"""Port pour interroger l'état Git d'un projet (commit actuel, fichiers changés)."""

from abc import ABC, abstractmethod
from typing import List


class GitPort(ABC):
    """Contrat pour tout composant capable de lire l'historique Git d'un projet."""

    @abstractmethod
    def get_current_commit_hash(self, project_root: str) -> "str | None":
        """Renvoie le hash du commit HEAD actuel, ou None si ce n'est pas un dépôt Git."""
        raise NotImplementedError

    @abstractmethod
    def get_changed_files_since(self, project_root: str, old_commit_hash: str) -> List[str]:
        """Renvoie la liste des fichiers modifiés/ajoutés/supprimés depuis un commit donné."""
        raise NotImplementedError

    @abstractmethod
    def clone_repository(self, repo_url: str, destination_path: str, branch: "str | None" = None) -> "str | None":
        """
        Clone un dépôt distant vers un chemin local. Renvoie None si le
        clonage a réussi, ou un message d'erreur (str) sinon.

        Args:
            repo_url: URL du dépôt à cloner (HTTPS ou SSH)
            destination_path: Chemin local où cloner le dépôt
            branch: Branche spécifique à cloner, ou None pour la branche par défaut
        """
        raise NotImplementedError