"""
Tests Sprint 32 : GitService
- is_git_repo
- get_status : working tree propre vs dirty
- pull : securise (refuse si dirty, accepte si propre)
- get_diff_summary : resume des fichiers modifies
- tool_sync_workspace : wrapper MCP
- tool_get_git_diff : wrapper MCP
"""

import pytest
from unittest.mock import patch, MagicMock
from services.git_service import GitService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _service():
    return GitService("/fake/repo")


def tool_sync_workspace(workspace_path: str, git_service) -> str:
    if not git_service.is_git_repo():
        return f"Le chemin '{workspace_path}' n'est pas un depot Git valide."
    try:
        status = git_service.get_status()
        if not status["is_clean"]:
            fichiers = status["modified"] + status["staged"]
            return (
                f"Synchronisation impossible : modifications locales non committees detectees.\n"
                f"Fichiers concernes : {', '.join(fichiers)}.\n"
                f"Committez ou stashez ces modifications avant de synchroniser."
            )
        resultat = git_service.pull()
        if resultat["deja_a_jour"]:
            return "Workspace deja a jour avec GitHub. Aucune modification recue."
        return (
            f"Workspace synchronise avec succes.\n"
            f"Fichiers mis a jour : {len(resultat['fichiers_mis_a_jour'])}"
        )
    except RuntimeError as e:
        return f"Erreur Git : {e}"
    except TimeoutError as e:
        return f"Timeout Git : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


def tool_get_git_diff(workspace_path: str, git_service) -> str:
    try:
        diff = git_service.get_diff_summary()
        if not diff["fichiers"]:
            return "Aucune modification detectee dans le dernier commit."
        return f"Fichiers modifies :\n{diff['resume']}"
    except Exception as e:
        return f"Erreur lors de la recuperation du diff : {e}"


# ── Tests GitService.is_git_repo ──────────────────────────────────────────────

class TestIsGitRepo:

    def test_retourne_true_si_repo_git(self):
        service = _service()
        with patch.object(service, '_run', return_value=(0, "true", "")):
            assert service.is_git_repo() is True

    def test_retourne_false_si_pas_repo_git(self):
        service = _service()
        with patch.object(service, '_run', return_value=(128, "", "not a git repository")):
            assert service.is_git_repo() is False


# ── Tests GitService.get_status ───────────────────────────────────────────────

class TestGetStatus:

    def test_working_tree_propre(self):
        service = _service()
        with patch.object(service, '_run', return_value=(0, "", "")):
            status = service.get_status()
        assert status["is_clean"] is True
        assert status["modified"] == []
        assert status["untracked"] == []

    def test_detecte_fichiers_modifies(self):
        service = _service()
        stdout = " M src/Controller/ProductController.php\n M templates/product/index.html.twig"
        with patch.object(service, '_run', return_value=(0, stdout, "")):
            status = service.get_status()
        assert status["is_clean"] is False
        assert "src/Controller/ProductController.php" in status["modified"]
        assert "templates/product/index.html.twig" in status["modified"]

    def test_detecte_fichiers_non_suivis(self):
        service = _service()
        stdout = "?? src/DataFixtures/AppFixtures.php"
        with patch.object(service, '_run', return_value=(0, stdout, "")):
            status = service.get_status()
        assert "src/DataFixtures/AppFixtures.php" in status["untracked"]

    def test_detecte_fichiers_en_staging(self):
        service = _service()
        stdout = "M  src/Entity/Product.php"
        with patch.object(service, '_run', return_value=(0, stdout, "")):
            status = service.get_status()
        assert "src/Entity/Product.php" in status["staged"]

    def test_leve_erreur_si_git_status_echoue(self):
        service = _service()
        with patch.object(service, '_run', return_value=(1, "", "fatal: not a git repo")):
            with pytest.raises(RuntimeError) as exc:
                service.get_status()
        assert "git status" in str(exc.value).lower()


# ── Tests GitService.pull ─────────────────────────────────────────────────────

class TestPull:

    def test_pull_reussi_si_working_tree_propre(self):
        service = _service()
        status_propre = {"is_clean": True, "modified": [], "untracked": [], "staged": []}
        pull_stdout = "Updating abc..def\nFast-forward\n src/Controller/ProductController.php | 10 +\n"

        with patch.object(service, 'get_status', return_value=status_propre), \
             patch.object(service, '_run', return_value=(0, pull_stdout, "")):
            resultat = service.pull()

        assert resultat["succes"] is True
        assert resultat["deja_a_jour"] is False

    def test_pull_refuse_si_modifications_locales(self):
        service = _service()
        status_dirty = {
            "is_clean": False,
            "modified": ["src/Controller/ProductController.php"],
            "untracked": [],
            "staged": [],
        }

        with patch.object(service, 'get_status', return_value=status_dirty):
            with pytest.raises(RuntimeError) as exc:
                service.pull()

        assert "modifications locales" in str(exc.value).lower()
        assert "ProductController.php" in str(exc.value)

    def test_pull_retourne_deja_a_jour(self):
        service = _service()
        status_propre = {"is_clean": True, "modified": [], "untracked": [], "staged": []}

        with patch.object(service, 'get_status', return_value=status_propre), \
             patch.object(service, '_run', return_value=(0, "Already up to date.", "")):
            resultat = service.pull()

        assert resultat["deja_a_jour"] is True

    def test_pull_leve_erreur_si_git_pull_echoue(self):
        service = _service()
        status_propre = {"is_clean": True, "modified": [], "untracked": [], "staged": []}

        with patch.object(service, 'get_status', return_value=status_propre), \
             patch.object(service, '_run', return_value=(1, "", "fatal: unable to access")):
            with pytest.raises(RuntimeError) as exc:
                service.pull()
        assert "git pull" in str(exc.value).lower()

    def test_pull_ne_fait_jamais_reset_hard(self):
        service = _service()
        calls = []

        def mock_run(args, timeout=30):
            calls.append(args)
            return (0, "Already up to date.", "")

        status_propre = {"is_clean": True, "modified": [], "untracked": [], "staged": []}
        with patch.object(service, 'get_status', return_value=status_propre), \
             patch.object(service, '_run', side_effect=mock_run):
            service.pull()

        for call_args in calls:
            assert "reset" not in call_args
            assert "--hard" not in call_args


# ── Tests GitService.get_diff_summary ─────────────────────────────────────────

class TestGetDiffSummary:

    def test_retourne_fichiers_modifies(self):
        service = _service()
        stdout = "M\tsrc/Controller/ProductController.php\nA\tsrc/Repository/ProductRepository.php"
        with patch.object(service, '_run', return_value=(0, stdout, "")):
            diff = service.get_diff_summary()

        assert len(diff["fichiers"]) == 2
        noms = [f["fichier"] for f in diff["fichiers"]]
        assert "src/Controller/ProductController.php" in noms

    def test_statuts_traduits_correctement(self):
        service = _service()
        stdout = "M\tfichier1.php\nA\tfichier2.php\nD\tfichier3.php"
        with patch.object(service, '_run', return_value=(0, stdout, "")):
            diff = service.get_diff_summary()

        statuts = {f["fichier"]: f["statut"] for f in diff["fichiers"]}
        assert statuts["fichier1.php"] == "modifie"
        assert statuts["fichier2.php"] == "ajoute"
        assert statuts["fichier3.php"] == "supprime"

    def test_retourne_dict_vide_si_aucune_modification(self):
        service = _service()
        with patch.object(service, '_run', return_value=(0, "", "")):
            diff = service.get_diff_summary()
        assert diff["fichiers"] == []
        assert "Aucune" in diff["resume"]


# ── Tests tool_sync_workspace ─────────────────────────────────────────────────

class TestToolSyncWorkspace:

    def test_retourne_erreur_si_pas_repo_git(self):
        service = _service()
        with patch.object(service, 'is_git_repo', return_value=False):
            resultat = tool_sync_workspace("/fake/repo", service)
        assert "pas un depot git" in resultat.lower()

    def test_retourne_erreur_si_modifications_locales(self):
        service = _service()
        with patch.object(service, 'is_git_repo', return_value=True), \
             patch.object(service, 'get_status', return_value={
                 "is_clean": False,
                 "modified": ["src/Controller/ProductController.php"],
                 "staged": [], "untracked": []
             }):
            resultat = tool_sync_workspace("/fake/repo", service)
        assert "impossible" in resultat.lower()
        assert "ProductController.php" in resultat

    def test_retourne_deja_a_jour(self):
        service = _service()
        with patch.object(service, 'is_git_repo', return_value=True), \
             patch.object(service, 'get_status', return_value={
                 "is_clean": True, "modified": [], "staged": [], "untracked": []
             }), \
             patch.object(service, 'pull', return_value={
                 "succes": True, "deja_a_jour": True,
                 "message": "Already up to date.", "fichiers_mis_a_jour": []
             }):
            resultat = tool_sync_workspace("/fake/repo", service)
        assert "deja a jour" in resultat.lower()

    def test_retourne_confirmation_si_pull_reussi(self):
        service = _service()
        with patch.object(service, 'is_git_repo', return_value=True), \
             patch.object(service, 'get_status', return_value={
                 "is_clean": True, "modified": [], "staged": [], "untracked": []
             }), \
             patch.object(service, 'pull', return_value={
                 "succes": True, "deja_a_jour": False,
                 "message": "Updating...", "fichiers_mis_a_jour": ["fichier1.php"]
             }):
            resultat = tool_sync_workspace("/fake/repo", service)
        assert "synchronise" in resultat.lower()


# ── Tests tool_get_git_diff ───────────────────────────────────────────────────

class TestToolGetGitDiff:

    def test_retourne_fichiers_modifies(self):
        service = _service()
        with patch.object(service, 'get_diff_summary', return_value={
            "fichiers": [{"fichier": "src/Controller/ProductController.php", "statut": "modifie"}],
            "resume": "- src/Controller/ProductController.php (modifie)"
        }):
            resultat = tool_get_git_diff("/fake/repo", service)
        assert "ProductController.php" in resultat

    def test_retourne_message_si_aucune_modification(self):
        service = _service()
        with patch.object(service, 'get_diff_summary', return_value={
            "fichiers": [], "resume": "Aucune modification detectee."
        }):
            resultat = tool_get_git_diff("/fake/repo", service)
        assert "Aucune" in resultat