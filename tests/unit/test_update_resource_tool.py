"""Vérifie le tool update_resource, fixtures génériques."""

from core.ports.git_port import GitPort
from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.chat_tools import ChatTools
from services.resource_generator_service import ResourceGeneratorService
from services.workspace_indexer_service import WorkspaceIndexerService
from services.workspace_service import WorkspaceService


class FakeGitPort(GitPort):
    def __init__(self, echec=None):
        self._echec = echec

    def get_current_commit_hash(self, project_root):
        return None

    def get_changed_files_since(self, project_root, old_commit_hash):
        return []

    def clone_repository(self, repo_url, destination_path, branch=None, auth_token=None):
        if self._echec:
            return self._echec
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


def _construire_tools(tmp_path, git_port=None):
    workspace_service = WorkspaceService(git_port or FakeGitPort(), str(tmp_path))
    resource_generator = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
    workspace_indexer = WorkspaceIndexerService(FakeCredentialsStore())
    tools = ChatTools(
        FakeContainer(), workspace_service=workspace_service,
        resource_generator=resource_generator, workspace_indexer=workspace_indexer,
    )
    return tools, workspace_service


def test_update_resource_modifie_reellement_le_fichier_sur_disque(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.update_resource("sample", "development_rules.md", "# Nouvelles regles\nUtiliser DDD.")

    assert "mise à jour" in resultat
    fichier = tmp_path / "sample" / "resources" / "development_rules.md"
    assert fichier.exists()
    assert fichier.read_text(encoding="utf-8") == "# Nouvelles regles\nUtiliser DDD."


def test_update_resource_peut_creer_une_toute_nouvelle_resource(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.update_resource("sample", "custom_ddd_rules.md", "# Regles DDD personnalisees")

    fichier = tmp_path / "sample" / "resources" / "custom_ddd_rules.md"
    assert fichier.exists()


def test_update_resource_refuse_un_workspace_introuvable(tmp_path):
    tools, _ = _construire_tools(tmp_path)

    resultat = tools.update_resource("n-existe-pas", "development_rules.md", "contenu")

    assert "introuvable" in resultat


def test_update_resource_refuse_un_workspace_en_erreur(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path, git_port=FakeGitPort(echec="erreur de clone"))
    workspace_service.create_workspace("https://example.com/user/sample.git")

    resultat = tools.update_resource("sample", "development_rules.md", "contenu")

    assert "erreur" in resultat