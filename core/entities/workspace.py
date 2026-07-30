"""
Entité centrale de la plateforme MCP générique : un Workspace représente
un dépôt Git importé, avec son propre cycle de vie.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WorkspaceStatus(str, Enum):
    """
    Chaque valeur représente l'étape ACTUELLEMENT en cours (pas la
    dernière terminée) -- ex: ANALYZING signifie "le clone a réussi,
    l'analyse est la prochaine étape attendue", même si le composant
    d'analyse n'est pas encore implémenté (sprint suivant).
    """

    CREATED = "created"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    GENERATING_RESOURCES = "generating_resources"
    INDEXING = "indexing"
    READY = "ready"
    SYNCING = "syncing"
    ARCHIVED = "archived"
    ERROR = "error"


@dataclass
class Workspace:
    """Un Workspace = un dépôt Git + son cycle de vie."""

    workspace_id: str  # slug, ex: "e-commerce"
    repo_url: str
    branch: Optional[str]
    status: WorkspaceStatus
    created_at: str  # ISO 8601
    error_message: Optional[str] = field(default=None)

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "status": self.status.value,
            "created_at": self.created_at,
            "error_message": self.error_message,
        }

    @staticmethod
    def from_dict(donnees: dict) -> "Workspace":
        return Workspace(
            workspace_id=donnees["workspace_id"],
            repo_url=donnees["repo_url"],
            branch=donnees.get("branch"),
            status=WorkspaceStatus(donnees["status"]),
            created_at=donnees["created_at"],
            error_message=donnees.get("error_message"),
        )