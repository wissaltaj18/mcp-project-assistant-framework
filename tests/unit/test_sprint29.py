"""
Tests Sprint 29 : update_jira_status
- get_transitions : récupère les transitions disponibles
- apply_transition : applique une transition par ID
- update_status : change le statut par nom lisible
- tool_update_jira_status : wrapper MCP
"""

import pytest
from unittest.mock import patch, MagicMock
from services.jira_service import JiraService
from config.jira_config import JiraConfig


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config():
    return JiraConfig(
        base_url="https://wissaltestmcp.atlassian.net",
        email="test@example.com",
        api_token="fake-token",
    )


def _service():
    return JiraService(_config())


def _transitions_jira():
    return {
        "transitions": [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
    }


def _tool_update_jira_status(ticket_id: str, status: str, jira_service) -> str:
    """Reproduit la logique du tool MCP server.py pour les tests."""
    if jira_service is None:
        return (
            "Jira non configuré. Ajoute JIRA_BASE_URL, JIRA_EMAIL et "
            "JIRA_API_TOKEN dans ton fichier .env."
        )
    if not ticket_id or not ticket_id.strip():
        return "Erreur : ticket_id est vide."
    if not status or not status.strip():
        return "Erreur : le statut demandé est vide."
    try:
        resultat = jira_service.update_status(ticket_id.strip(), status.strip())
        return (
            f"Statut du ticket {resultat['ticket_id']} mis à jour avec succès : "
            f"{resultat['nouveau_statut']}."
        )
    except FileNotFoundError:
        return f"Ticket '{ticket_id}' introuvable sur Jira."
    except PermissionError as e:
        return f"Erreur d'authentification Jira : {e}"
    except ValueError as e:
        return f"Erreur de transition : {e}"
    except (ConnectionError, TimeoutError) as e:
        return f"Erreur réseau Jira : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


# ── Tests get_transitions ─────────────────────────────────────────────────────

class TestGetTransitions:

    def test_retourne_liste_transitions_disponibles(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _transitions_jira()

        with patch("requests.get", return_value=mock_resp):
            transitions = _service().get_transitions("KAN-4")

        assert len(transitions) == 3
        noms = [t["name"] for t in transitions]
        assert "In Progress" in noms
        assert "Done" in noms

    def test_retourne_liste_vide_si_aucune_transition(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"transitions": []}

        with patch("requests.get", return_value=mock_resp):
            transitions = _service().get_transitions("KAN-4")

        assert transitions == []

    def test_leve_erreur_404_ticket_introuvable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(FileNotFoundError) as exc:
                _service().get_transitions("KAN-999")
        assert "KAN-999" in str(exc.value)

    def test_leve_erreur_401_auth_invalide(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(PermissionError):
                _service().get_transitions("KAN-4")

    def test_leve_connection_error(self):
        import requests as req
        with patch("requests.get", side_effect=req.ConnectionError()):
            with pytest.raises(ConnectionError):
                _service().get_transitions("KAN-4")


# ── Tests apply_transition ────────────────────────────────────────────────────

class TestApplyTransition:

    def test_applique_transition_avec_succes(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with patch("requests.post", return_value=mock_resp):
            resultat = _service().apply_transition("KAN-4", "21")

        assert resultat["succes"] is True
        assert resultat["ticket_id"] == "KAN-4"
        assert resultat["transition_id"] == "21"

    def test_leve_erreur_400_transition_invalide(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 400

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(ValueError) as exc:
                _service().apply_transition("KAN-4", "999")
        assert "invalide" in str(exc.value).lower()

    def test_leve_erreur_404_ticket_introuvable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(FileNotFoundError):
                _service().apply_transition("KAN-999", "21")


# ── Tests update_status ───────────────────────────────────────────────────────

class TestUpdateStatus:

    def _mock_get(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _transitions_jira()
        return mock_resp

    def _mock_post(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        return mock_resp

    def test_passe_ticket_en_in_progress(self):
        with patch("requests.get", return_value=self._mock_get()), \
             patch("requests.post", return_value=self._mock_post()):
            resultat = _service().update_status("KAN-4", "In Progress")

        assert resultat["succes"] is True
        assert resultat["nouveau_statut"] == "In Progress"
        assert resultat["ticket_id"] == "KAN-4"
        assert resultat["transition_id"] == "21"

    def test_passe_ticket_en_done(self):
        with patch("requests.get", return_value=self._mock_get()), \
             patch("requests.post", return_value=self._mock_post()):
            resultat = _service().update_status("KAN-4", "Done")

        assert resultat["nouveau_statut"] == "Done"
        assert resultat["transition_id"] == "31"

    def test_insensible_a_la_casse(self):
        with patch("requests.get", return_value=self._mock_get()), \
             patch("requests.post", return_value=self._mock_post()):
            resultat = _service().update_status("KAN-4", "in progress")

        assert resultat["nouveau_statut"] == "In Progress"

    def test_leve_erreur_si_statut_inexistant(self):
        with patch("requests.get", return_value=self._mock_get()):
            with pytest.raises(ValueError) as exc:
                _service().update_status("KAN-4", "Review")
        assert "Review" in str(exc.value)
        assert "In Progress" in str(exc.value) or "To Do" in str(exc.value)

    def test_leve_erreur_si_aucune_transition_disponible(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"transitions": []}

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(ValueError) as exc:
                _service().update_status("KAN-4", "Done")
        assert "Aucune transition" in str(exc.value)


# ── Tests tool_update_jira_status ─────────────────────────────────────────────

class TestToolUpdateJiraStatus:

    def test_retourne_erreur_si_jira_non_configure(self):
        resultat = _tool_update_jira_status("KAN-4", "In Progress", None)
        assert "non configur" in resultat.lower()

    def test_retourne_erreur_si_ticket_id_vide(self):
        resultat = _tool_update_jira_status("", "In Progress", _service())
        assert "vide" in resultat.lower()

    def test_retourne_erreur_si_statut_vide(self):
        resultat = _tool_update_jira_status("KAN-4", "", _service())
        assert "vide" in resultat.lower()

    def test_retourne_confirmation_si_succes(self):
        mock_get = MagicMock()
        mock_get.status_code = 200
        mock_get.json.return_value = _transitions_jira()
        mock_post = MagicMock()
        mock_post.status_code = 204

        with patch("requests.get", return_value=mock_get), \
             patch("requests.post", return_value=mock_post):
            resultat = _tool_update_jira_status("KAN-4", "In Progress", _service())

        assert "KAN-4" in resultat
        assert "In Progress" in resultat

    def test_retourne_erreur_si_statut_inexistant(self):
        mock_get = MagicMock()
        mock_get.status_code = 200
        mock_get.json.return_value = _transitions_jira()

        with patch("requests.get", return_value=mock_get):
            resultat = _tool_update_jira_status("KAN-4", "StatutInexistant", _service())

        assert "Erreur de transition" in resultat
        assert "StatutInexistant" in resultat

    def test_retourne_erreur_si_ticket_introuvable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.get", return_value=mock_resp):
            resultat = _tool_update_jira_status("KAN-999", "In Progress", _service())

        assert "introuvable" in resultat.lower()