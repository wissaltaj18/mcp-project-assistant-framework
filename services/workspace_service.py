"""
Orchestrateur central de la plateforme MCP générique : crée, persiste, et
liste les Workspaces. Ce sprint couvre uniquement CREATED -> CLONING ->
(ANALYZING | ERROR).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from core.entities.workspace import Workspace, WorkspaceStatus
from core.ports.git_port import GitPort


class WorkspaceAlreadyExistsError(Exception):
    """Levée quand un Workspace avec le même slug existe déjà."""


class WorkspaceService:
    """Cas d'usage : créer un Workspace depuis une URL de dépôt, le persister, le retrouver."""

    def __init__(self, git_provider: GitPort, workspaces_dir: str):
        self._git = git_provider
        self._workspaces_dir = Path(workspaces_dir)

    def _deriver_slug(self, repo_url: str) -> str:
        nom_brut = re.sub(r"\.git$", "", repo_url.rstrip("/").split("/")[-1])
        slug = nom_brut.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        if not slug:
            raise ValueError(f"Impossible de dériver un identifiant valide depuis l'URL : '{repo_url}'")
        return slug

    def _chemin_workspace(self, workspace_id: str) -> Path:
        return self._workspaces_dir / workspace_id

    def _chemin_metadata(self, workspace_id: str) -> Path:
        return self._chemin_workspace(workspace_id) / "workspace.json"

    def _sauvegarder(self, workspace: Workspace) -> None:
        chemin = self._chemin_metadata(workspace.workspace_id)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(workspace.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def create_workspace(self, repo_url: str, branch: Optional[str] = None) -> Workspace:
        workspace_id = self._deriver_slug(repo_url)

        if self._chemin_metadata(workspace_id).exists():
            raise WorkspaceAlreadyExistsError(
                f"Un Workspace nommé '{workspace_id}' existe déjà. "
                f"Utilise get_workspace('{workspace_id}') ou choisis un autre dépôt."
            )

        workspace = Workspace(
            workspace_id=workspace_id,
            repo_url=repo_url,
            branch=branch,
            status=WorkspaceStatus.CLONING,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sauvegarder(workspace)

        chemin_repo = self._chemin_workspace(workspace_id) / "repo"
        erreur = self._git.clone_repository(repo_url, str(chemin_repo), branch)

        if erreur is not None:
            workspace.status = WorkspaceStatus.ERROR
            workspace.error_message = erreur
            self._sauvegarder(workspace)
            return workspace

        workspace.status = WorkspaceStatus.ANALYZING
        self._sauvegarder(workspace)
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        chemin = self._chemin_metadata(workspace_id)
        if not chemin.exists():
            return None
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        return Workspace.from_dict(donnees)

    def list_workspaces(self) -> List[Workspace]:
        if not self._workspaces_dir.exists():
            return []
        workspaces = []
        for dossier in sorted(self._workspaces_dir.iterdir()):
            chemin_metadata = dossier / "workspace.json"
            if chemin_metadata.exists():
                donnees = json.loads(chemin_metadata.read_text(encoding="utf-8"))
                workspaces.append(Workspace.from_dict(donnees))
        return workspaces