"""Vérifie le tool create_workspace, sans dépendance à un projet particulier."""

from core.ports.git_port import GitPort
from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.chat_tools import ChatTools
from services.resource_generator_service import ResourceGeneratorService
from services.workspace_indexer_service import WorkspaceIndexerService
from services.workspace_service import WorkspaceService


class FakeGitPort(GitPort):
    def get_current_commit_hash(self, project_root: str):
        return None

    def get_changed_files_since(self, project_root: str, old_commit_hash: str):
        return []

    def clone_repository(self, repo_url: str, destination_path: str, branch=None, auth_token=None):
        import os
        os.makedirs(destination_path, exist_ok=True)
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


def test_create_workspace_tool_cree_reellement_un_workspace(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    tools = ChatTools(FakeContainer(), workspace_service=workspace_service, **_kwargs_workspace())

    resultat = tools.create_workspace("https://example.com/user/sample.git")

    assert "sample" in resultat
    assert "créé avec succès" in resultat
    assert workspace_service.get_workspace("sample") is not None


def test_create_workspace_tool_ne_modifie_pas_letat_de_chat_tools(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    tools = ChatTools(
        FakeContainer(), repo_path="/chemin/initial",
        workspace_service=workspace_service, **_kwargs_workspace(),
    )

    tools.create_workspace("https://example.com/user/sample.git")

    assert tools._chemin_projet_complet == "/chemin/initial"