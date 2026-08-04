"""Vérifie prepare_workspace, orchestration complète sans dupliquer la logique existante."""

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
    return tools


def test_prepare_workspace_enchaine_les_4_etapes_avec_succes(tmp_path):
    tools = _construire_tools(tmp_path)

    resultat = tools.prepare_workspace("https://example.com/user/sample.git")

    assert "entièrement préparé et actif" in resultat
    assert "Création : OK" in resultat
    assert "Activation : OK" in resultat


def test_prepare_workspace_active_reellement_le_workspace(tmp_path):
    """Preuve concrète de l'activation automatique : le chemin actif de ChatTools a changé."""
    tools = _construire_tools(tmp_path)
    chemin_avant = tools._chemin_projet_complet

    tools.prepare_workspace("https://example.com/user/sample.git")

    assert tools._chemin_projet_complet != chemin_avant
    assert "sample" in tools._chemin_projet_complet


def test_prepare_workspace_genere_reellement_les_resources_sur_disque(tmp_path):
    tools = _construire_tools(tmp_path)

    tools.prepare_workspace("https://example.com/user/sample.git")

    fichier = tmp_path / "sample" / "resources" / "technical_architecture.md"
    assert fichier.exists()


def test_prepare_workspace_sarrete_proprement_si_le_clone_echoue(tmp_path):
    tools = _construire_tools(tmp_path, git_port=FakeGitPort(echec="dépôt introuvable"))

    resultat = tools.prepare_workspace("https://example.com/user/sample.git")

    assert "interrompue" in resultat
    assert "dépôt introuvable" in resultat
    # Aucune Resource ne doit avoir été générée après un échec de clone
    assert not (tmp_path / "sample" / "resources").exists()


def test_prepare_workspace_refuse_un_workspace_deja_existant(tmp_path):
    tools = _construire_tools(tmp_path)
    tools.create_workspace("https://example.com/user/sample.git")

    resultat = tools.prepare_workspace("https://example.com/user/sample.git")

    assert "interrompue" in resultat
    assert "existe déjà" in resultat