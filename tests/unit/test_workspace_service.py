"""Tests unitaires de WorkspaceService, avec un FakeGitPort (aucun accès réseau réel)."""

import json

import pytest

from core.entities.workspace import WorkspaceStatus
from core.ports.git_port import GitPort
from services.workspace_service import WorkspaceAlreadyExistsError, WorkspaceService


class FakeGitPort(GitPort):
    def __init__(self, echec: "str | None" = None):
        self._echec = echec
        self.dernier_appel = None

    def get_current_commit_hash(self, project_root: str) -> "str | None":
        return None

    def get_changed_files_since(self, project_root: str, old_commit_hash: str):
        return []

    def clone_repository(self, repo_url: str, destination_path: str, branch=None, auth_token=None) -> "str | None":
        self.dernier_appel = {"repo_url": repo_url, "destination_path": destination_path, "branch": branch}
        if self._echec:
            return self._echec
        import os
        os.makedirs(destination_path, exist_ok=True)
        with open(os.path.join(destination_path, "README.md"), "w") as f:
            f.write("Dépôt simulé")
        return None


@pytest.fixture
def workspaces_dir_temporaire(tmp_path):
    return str(tmp_path / "workspaces")


def test_create_workspace_derive_le_bon_slug(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    workspace = service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")
    assert workspace.workspace_id == "e-commerce"


def test_create_workspace_succes_termine_en_analyzing(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    workspace = service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")
    assert workspace.status == WorkspaceStatus.ANALYZING
    assert workspace.error_message is None


def test_create_workspace_echec_termine_en_error_avec_message(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(echec="dépôt introuvable"), workspaces_dir_temporaire)
    workspace = service.create_workspace("https://github.com/x/inexistant.git")
    assert workspace.status == WorkspaceStatus.ERROR
    assert workspace.error_message == "dépôt introuvable"


def test_create_workspace_persiste_reellement_sur_disque(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")

    chemin_json = f"{workspaces_dir_temporaire}/e-commerce/workspace.json"
    with open(chemin_json, encoding="utf-8") as f:
        donnees = json.load(f)
    assert donnees["status"] == "analyzing"
    assert donnees["repo_url"] == "https://github.com/wissaltaj18/E-commerce.git"


def test_create_workspace_refuse_un_doublon(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")
    with pytest.raises(WorkspaceAlreadyExistsError):
        service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")


def test_create_workspace_transmet_bien_la_branche_au_git_port(workspaces_dir_temporaire):
    fake_git = FakeGitPort()
    service = WorkspaceService(fake_git, workspaces_dir_temporaire)
    service.create_workspace("https://github.com/wissaltaj18/E-commerce.git", branch="develop")
    assert fake_git.dernier_appel["branch"] == "develop"


def test_get_workspace_recharge_bien_depuis_le_disque(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    cree = service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")
    recharge = service.get_workspace("e-commerce")
    assert recharge is not None
    assert recharge.workspace_id == cree.workspace_id
    assert recharge.status == cree.status


def test_get_workspace_inexistant_renvoie_none(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    assert service.get_workspace("n-existe-pas") is None


def test_list_workspaces_renvoie_tous_les_workspaces_crees(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    service.create_workspace("https://github.com/wissaltaj18/E-commerce.git")
    service.create_workspace("https://github.com/autre-utilisateur/autre-projet.git")
    workspaces = service.list_workspaces()
    ids = sorted(w.workspace_id for w in workspaces)
    assert ids == ["autre-projet", "e-commerce"]


def test_list_workspaces_vide_si_aucun_workspace(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    assert service.list_workspaces() == []


def test_slug_derive_correctement_avec_url_se_terminant_par_slash(workspaces_dir_temporaire):
    service = WorkspaceService(FakeGitPort(), workspaces_dir_temporaire)
    workspace = service.create_workspace("https://github.com/wissaltaj18/E-commerce/")
    assert workspace.workspace_id == "e-commerce"