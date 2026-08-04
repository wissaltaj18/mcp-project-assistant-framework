"""
Vérifie que ChatTools devient Workspace-aware via repo_path, tout en
gardant la rétrocompatibilité totale avec l'ancien mode.
"""

from core.ports.git_port import GitPort
from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.chat_tools import ChatTools
from services.resource_generator_service import ResourceGeneratorService
from services.workspace_indexer_service import WorkspaceIndexerService
from services.workspace_service import WorkspaceService


class FakeGitPortMinimal(GitPort):
    def get_current_commit_hash(self, project_root: str):
        return None

    def get_changed_files_since(self, project_root: str, old_commit_hash: str):
        return []

    def clone_repository(self, repo_url: str, destination_path: str, branch=None, auth_token=None):
        return None


class FakeCredentialsStore:
    def get(self, key: str):
        return None


class FakeSettings:
    generated_projects_dir = "generated_projects"


class FakeContainer:
    settings = FakeSettings()


def _kwargs_workspace(tmp_path):
    return dict(
        resource_generator=ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter()),
        workspace_indexer=WorkspaceIndexerService(FakeCredentialsStore()),
    )


def test_chat_tools_utilise_le_repo_path_explicite_si_fourni(tmp_path):
    (tmp_path / "example.py").write_text("def run():\n    pass")
    workspace_service = WorkspaceService(FakeGitPortMinimal(), str(tmp_path / "_ws"))
    tools = ChatTools(
        FakeContainer(), repo_path=str(tmp_path),
        workspace_service=workspace_service, **_kwargs_workspace(tmp_path),
    )
    assert tools._chemin_projet_complet == str(tmp_path)
    assert "example.py" in tools.get_project_structure()


def test_chat_tools_retrocompatible_sans_repo_path(tmp_path):
    workspace_service = WorkspaceService(FakeGitPortMinimal(), str(tmp_path / "_ws"))
    tools = ChatTools(
        FakeContainer(), project_name="demo-rh",
        workspace_service=workspace_service, **_kwargs_workspace(tmp_path),
    )
    assert tools._chemin_projet_complet == "generated_projects/demo-rh"


def test_chat_tools_gere_correctement_une_chaine_vide(tmp_path):
    workspace_service = WorkspaceService(FakeGitPortMinimal(), str(tmp_path / "_ws"))
    tools = ChatTools(
        FakeContainer(), repo_path="",
        workspace_service=workspace_service, **_kwargs_workspace(tmp_path),
    )
    assert tools._chemin_projet_complet == ""