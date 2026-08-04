"""
Vérifie la correction de l'incohérence de chemin RAG (Sprint 14) :
search_knowledge_base/index_project (legacy) doivent utiliser le MEME
chemin qu'index_workspace écrit, une fois qu'un Workspace est actif --
sans Workspace actif, le comportement legacy reste inchangé.
"""

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


def _construire_tools(tmp_path):
    workspace_service = WorkspaceService(FakeGitPort(), str(tmp_path))
    resource_generator = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
    workspace_indexer = WorkspaceIndexerService(FakeCredentialsStore())
    tools = ChatTools(
        FakeContainer(), workspace_service=workspace_service,
        resource_generator=resource_generator, workspace_indexer=workspace_indexer,
    )
    return tools, workspace_service


def test_mode_legacy_sans_workspace_actif_comportement_inchange(tmp_path):
    """Sans Workspace actif, le chemin reste exactement celui d'avant (rétrocompatibilité)."""
    tools, _ = _construire_tools(tmp_path)

    chemin = tools._resoudre_chemin_knowledge_base()

    assert chemin == f"{tools._chemin_projet_complet}/.knowledge_base.json"


def test_set_active_workspace_stocke_bien_lidentifiant(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")

    assert tools._active_workspace_id is None
    tools.set_active_workspace("sample")
    assert tools._active_workspace_id == "sample"


def test_le_chemin_legacy_correspond_maintenant_exactement_a_celui_dindex_workspace(tmp_path):
    """LA preuve du correctif : les deux chemins, autrefois différents, convergent."""
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/sample.git")
    tools.set_active_workspace("sample")

    chemin_utilise_par_search_knowledge_base = tools._resoudre_chemin_knowledge_base()
    chemin_ecrit_par_index_workspace = workspace_service.get_knowledge_base_path("sample")

    assert chemin_utilise_par_search_knowledge_base == chemin_ecrit_par_index_workspace


def test_reactiver_un_autre_workspace_change_bien_le_chemin_resolu(tmp_path):
    tools, workspace_service = _construire_tools(tmp_path)
    workspace_service.create_workspace("https://example.com/user/premier.git")
    workspace_service.create_workspace("https://example.com/user/second.git")

    tools.set_active_workspace("premier")
    chemin_premier = tools._resoudre_chemin_knowledge_base()

    tools.set_active_workspace("second")
    chemin_second = tools._resoudre_chemin_knowledge_base()

    assert chemin_premier != chemin_second
    assert "premier" in chemin_premier
    assert "second" in chemin_second