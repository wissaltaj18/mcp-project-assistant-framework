"""
Orchestrateur central de la plateforme MCP générique : crée, persiste, et
liste les Workspaces. Ce sprint couvre uniquement CREATED -> CLONING ->
(ANALYZING | ERROR) -- l'analyse, la génération de Resources et
l'indexation arrivent aux sprints suivants, sans modifier ce fichier.
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
        """Dérive un identifiant de dossier propre depuis une URL de dépôt (ex: .../E-commerce.git -> e-commerce)."""
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

    def get_repo_path(self, workspace_id: str) -> str:
        """Chemin absolu du dépôt cloné pour ce Workspace -- source unique de vérité pour cette convention."""
        return str(self._chemin_workspace(workspace_id) / "repo")

    def get_resources_path(self, workspace_id: str) -> str:
        """Chemin absolu du dossier Resources pour ce Workspace -- même convention que get_repo_path."""
        return str(self._chemin_workspace(workspace_id) / "resources")

    def get_knowledge_base_path(self, workspace_id: str) -> str:
        """Chemin absolu de la base vectorielle pour ce Workspace -- jamais à l'intérieur du dépôt cloné."""
        return str(self._chemin_workspace(workspace_id) / "knowledge_base.json")
    def get_preferences_path(self, workspace_id: str) -> str:
        return str(self._chemin_workspace(workspace_id) / "preferences.json")

    def get_preferences(self, workspace_id: str):
        from core.entities.workspace_preferences import WorkspacePreferences
        import json as _json
        chemin = self.get_preferences_path(workspace_id)
        try:
            with open(chemin, encoding="utf-8") as f:
                return WorkspacePreferences.from_dict(_json.load(f))
        except (FileNotFoundError, _json.JSONDecodeError):
            return WorkspacePreferences()

    def save_preferences(self, workspace_id: str, preferences) -> None:
        import json as _json
        from pathlib import Path as _Path
        chemin = _Path(self.get_preferences_path(workspace_id))
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(_json.dumps(preferences.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    def _sauvegarder(self, workspace: Workspace) -> None:
        chemin = self._chemin_metadata(workspace.workspace_id)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(workspace.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def create_workspace(self, repo_url: str, branch: Optional[str] = None, auth_token: Optional[str] = None) -> Workspace:
        """
        Crée un nouveau Workspace : dérive son identifiant, clone le
        dépôt, persiste son état. Lève WorkspaceAlreadyExistsError si un
        Workspace du même nom existe déjà (jamais d'écrasement silencieux).
        """
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
        erreur = self._git.clone_repository(repo_url, str(chemin_repo), branch, auth_token)

        if erreur is not None:
            workspace.status = WorkspaceStatus.ERROR
            workspace.error_message = erreur
            self._sauvegarder(workspace)
            return workspace

        workspace.status = WorkspaceStatus.ANALYZING
        self._sauvegarder(workspace)
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Recharge un Workspace depuis son fichier de métadonnées, ou None s'il n'existe pas."""
        chemin = self._chemin_metadata(workspace_id)
        if not chemin.exists():
            return None
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        return Workspace.from_dict(donnees)

    def list_workspaces(self) -> List[Workspace]:
        """Liste tous les Workspaces existants, triés par identifiant."""
        if not self._workspaces_dir.exists():
            return []
        workspaces = []
        for dossier in sorted(self._workspaces_dir.iterdir()):
            chemin_metadata = dossier / "workspace.json"
            if chemin_metadata.exists():
                donnees = json.loads(chemin_metadata.read_text(encoding="utf-8"))
                workspaces.append(Workspace.from_dict(donnees))
        return workspaces