"""Vérifie le tool set_preference et la persistance des préférences."""

from core.ports.git_port import GitPort
from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.chat_tools import ChatTools
from services.resource_generator_service import ResourceGeneratorService
from services.workspace_indexer_service import WorkspaceIndexerService
from services.workspace_service import WorkspaceService


class FakeGitPort(GitPort):
    def get_current_commit_hash(self, project_root):
        return None

    def get_changed_files_since(self, project_root, old_commit_hash):
        return []

    def clone_repository(self, repo_url, destination_path, branch=None, auth_token=None):
        import os
        os.makedirs(destination_path, exist_ok=True)
        return None


class FakeCredentialsStore:
    def get(self, key):
        return None


class FakeSettings:
    generated_projects_dir = "generated_projects"


class FakeContainer:
    settings = FakeSettings()


def _construire_tools(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    resource_generator = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
    workspace_indexer = WorkspaceIndexerService(FakeCredentialsStore())
    tools = ChatTools(
        FakeContainer(), workspace_service=workspace_service,
        resource_generator=resource_generator, workspace_indexer=workspace_indexer,
    )
    return tools, workspace_service


def test_set_preference_persiste_reellement_sur_disque(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.set_preference("sample", "run_tests_before_push", "false")

    assert "enregistrée" in resultat
    preferences = workspace_service.get_preferences("sample")
    assert preferences.get("run_tests_before_push") == "false"


def test_set_preference_refuse_un_workspace_introuvable(tmp_path):
    tools, _ = _construire_tools(tmp_path)

    resultat = tools.set_preference("n-existe-pas", "run_tests_before_push", "false")

    assert "introuvable" in resultat


def test_get_preferences_sans_fichier_renvoie_prefs_vides(tmp_path):
    _, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    preferences = workspace_service.get_preferences("sample")

    assert preferences.get("run_tests_before_push") is None