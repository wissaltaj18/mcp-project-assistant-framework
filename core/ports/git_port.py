"""Port pour interroger l'état Git d'un projet et cloner un dépôt (avec authentification optionnelle)."""

from abc import ABC, abstractmethod
from typing import List, Optional


class GitPort(ABC):
    """Contrat pour tout composant capable de lire l'historique Git d'un projet ou d'en cloner un."""

    @abstractmethod
    def get_current_commit_hash(self, project_root: str) -> "str | None":
        raise NotImplementedError

    @abstractmethod
    def get_changed_files_since(self, project_root: str, old_commit_hash: str) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def clone_repository(self, repo_url: str, destination_path: str, branch: Optional[str] = None, auth_token: Optional[str] = None) -> "str | None":
        """
        Clone un dépôt distant. Si auth_token est fourni (dépôt privé),
        il est utilisé UNIQUEMENT pendant le clone -- jamais persisté sur
        disque, jamais dans un message d'erreur renvoyé.
        """
        raise NotImplementedError