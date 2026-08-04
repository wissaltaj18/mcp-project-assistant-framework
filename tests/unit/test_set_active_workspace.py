"""Vérifie set_active_workspace, avec des fixtures génériques."""

from core.ports.git_port import GitPort
from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.chat_tools import ChatTools
from services.resource_generator_service import ResourceGeneratorService
from services.workspace_indexer_service import WorkspaceIndexerService
from services.workspace_service import WorkspaceService


class FakeGitPort(GitPort):
    def __init__(self, echec: "str | None" = None):
        self._echec = echec

    def get_current_commit_hash(self, project_root: str):
        return None

    def get_changed_files_since(self, project_root: str, old_commit_hash: str):
        return []

    def clone_repository(self, repo_url: str, destination_path: str, branch=None, auth_token=None):
        if self._echec:
            return self._echec
        import os
        os.makedirs(destination_path, exist_ok=True)
        with open(os.path.join(destination_path, "example.py"), "w") as f:
            f.write("def run(): pass")
        return None


class FakeCredentialsStore:
    def get(self, key: str):
        return None


class FakeSettings:
    generated_projects_dir = "generated_projects"


class FakeContainer:
    settings = FakeSettings()


def _kwargs_workspace():
    return dict(
        resource_generator=ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter()),
        workspace_indexer=WorkspaceIndexerService(FakeCredentialsStore()),
    )


def test_set_active_workspace_change_le_chemin_actif(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    tools = ChatTools(FakeContainer(), workspace_service=workspace_service, **_kwargs_workspace())
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.set_active_workspace("sample")

    assert "activé" in resultat
    assert "example.py" in tools.get_project_structure()


def test_set_active_workspace_vide_les_caches_pour_eviter_de_lire_lancien_workspace(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    tools = ChatTools(FakeContainer(), workspace_service=workspace_service, **_kwargs_workspace())

    tools._plan_storage = "ancien_cache_pas_encore_vide"
    tools._audit_logger = "ancien_cache_pas_encore_vide"

    workspace_service.create_workspace("https://example.com/user/sample.git")
    tools.set_active_workspace("sample")

    assert tools._plan_storage is None
    assert tools._audit_logger is None


def test_set_active_workspace_refuse_un_workspace_introuvable(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    tools = ChatTools(FakeContainer(), workspace_service=workspace_service, **_kwargs_workspace())

    resultat = tools.set_active_workspace("n-existe-pas")

    assert "introuvable" in resultat


def test_set_active_workspace_refuse_un_workspace_en_erreur(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(echec="dépôt introuvable"), str(tmp_path))
    tools = ChatTools(FakeContainer(), workspace_service=workspace_service, **_kwargs_workspace())
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.set_active_workspace("sample")

    assert "erreur" in resultat