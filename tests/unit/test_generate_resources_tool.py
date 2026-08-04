"""Vérifie le tool generate_resources, sans dépendance à un Workspace actif ni à un projet métier."""

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


def _construire_tools(tmp_path, git_port=None):
    workspace_service = WorkspaceService(git_port or FakeGitPort(), str(tmp_path))
    resource_generator = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
    workspace_indexer = WorkspaceIndexerService(FakeCredentialsStore())
    tools = ChatTools(
        FakeContainer(), workspace_service=workspace_service,
        resource_generator=resource_generator, workspace_indexer=workspace_indexer,
    )
    return tools, workspace_service


def test_generate_resources_ecrit_reellement_le_fichier_sur_disque(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.generate_resources("sample")

    assert "générées" in resultat
    fichier = tmp_path / "sample" / "resources" / "technical_architecture.md"
    assert fichier.exists()
    assert "Python" in fichier.read_text(encoding="utf-8")


def test_generate_resources_ne_depend_pas_dun_workspace_actif(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.generate_resources("sample")

    assert "sample" in resultat


def test_generate_resources_refuse_un_workspace_introuvable(tmp_path):
    tools, _ = _construire_tools(tmp_path)

    resultat = tools.generate_resources("n-existe-pas")

    assert "introuvable" in resultat


def test_generate_resources_refuse_un_workspace_en_erreur(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path, git_port=FakeGitPort(echec="dépôt introuvable"))
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.generate_resources("sample")

    assert "erreur" in resultat