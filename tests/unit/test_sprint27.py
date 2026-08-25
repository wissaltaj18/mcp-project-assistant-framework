"""
Tests Sprint 27 : JiraConfig + JiraService
Aucun appel réseau réel -- tout est mocké via unittest.mock.patch.
"""

import pytest
from unittest.mock import patch, MagicMock
from config.jira_config import JiraConfig
from services.jira_service import JiraService


# ── JiraConfig ───────────────────────────────────────────────────────────────

class TestJiraConfig:

    def test_charge_depuis_env(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "mon-token-secret")
        config = JiraConfig.from_env()
        assert config.base_url == "https://test.atlassian.net"
        assert config.email == "test@example.com"
        assert config.api_token == "mon-token-secret"

    def test_supprime_slash_final_de_base_url(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net/")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        config = JiraConfig.from_env()
        assert not config.base_url.endswith("/")

    def test_leve_erreur_si_token_manquant(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        with pytest.raises(ValueError) as exc:
            JiraConfig.from_env()
        assert "JIRA_API_TOKEN" in str(exc.value)

    def test_leve_erreur_si_email_manquant(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        with pytest.raises(ValueError) as exc:
            JiraConfig.from_env()
        assert "JIRA_EMAIL" in str(exc.value)

    def test_leve_erreur_si_url_manquante(self, monkeypatch):
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        with pytest.raises(ValueError) as exc:
            JiraConfig.from_env()
        assert "JIRA_BASE_URL" in str(exc.value)

    def test_message_erreur_liste_toutes_les_variables_manquantes(self, monkeypatch):
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        with pytest.raises(ValueError) as exc:
            JiraConfig.from_env()
        msg = str(exc.value)
        assert "JIRA_BASE_URL" in msg
        assert "JIRA_EMAIL" in msg
        assert "JIRA_API_TOKEN" in msg

    def test_is_configured_retourne_true_si_tout_present(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        config = JiraConfig(base_url="x", email="x", api_token="x")
        assert config.is_configured() is True

    def test_is_configured_retourne_false_si_token_manquant(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        config = JiraConfig(base_url="x", email="x", api_token="x")
        assert config.is_configured() is False


# ── Fixture commune ───────────────────────────────────────────────────────────

def _config_test():
    return JiraConfig(
        base_url="https://wissaltestmcp.atlassian.net",
        email="test@example.com",
        api_token="fake-token",
    )


def _reponse_jira_valide():
    return {
        "key": "KAN-4",
        "fields": {
            "summary": "Ajouter un filtre par categorie",
            "status": {"name": "To Do"},
            "priority": {"name": "Medium"},
            "issuetype": {"name": "Task"},
            "project": {"name": "Kanban"},
            "assignee": {"displayName": "Wissal Taj"},
            "reporter": {"displayName": "Admin"},
            "created": "2026-08-10T10:00:00.000+0000",
            "updated": "2026-08-10T11:00:00.000+0000",
            "labels": ["backend", "feature"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Ajouter un champ de filtrage"}]
                    }
                ]
            }
        }
    }


# ── JiraService.get_ticket ────────────────────────────────────────────────────

class TestJiraServiceGetTicket:

    def test_retourne_ticket_valide(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _reponse_jira_valide()

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            ticket = service.get_ticket("KAN-4")

        assert ticket["id"] == "KAN-4"
        assert ticket["titre"] == "Ajouter un filtre par categorie"
        assert ticket["statut"] == "To Do"
        assert ticket["priorite"] == "Medium"
        assert ticket["assignee"] == "Wissal Taj"
        assert ticket["labels"] == ["backend", "feature"]
        assert ticket["cree_le"] == "2026-08-10"

    def test_extrait_description_adf(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _reponse_jira_valide()

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            ticket = service.get_ticket("KAN-4")

        assert "filtrage" in ticket["description"]

    def test_leve_erreur_401_authentification_invalide(self):
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            with pytest.raises(PermissionError) as exc:
                service.get_ticket("KAN-4")
        assert "Authentification" in str(exc.value)

    def test_leve_erreur_404_ticket_introuvable(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            with pytest.raises(FileNotFoundError) as exc:
                service.get_ticket("KAN-999")
        assert "KAN-999" in str(exc.value)

    def test_leve_erreur_403_acces_refuse(self):
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            with pytest.raises(PermissionError) as exc:
                service.get_ticket("KAN-4")
        assert "refus" in str(exc.value).lower()

    def test_leve_connection_error_si_reseau_inaccessible(self):
        import requests as req
        with patch("requests.get", side_effect=req.ConnectionError()):
            service = JiraService(_config_test())
            with pytest.raises(ConnectionError) as exc:
                service.get_ticket("KAN-4")
        assert "joindre Jira" in str(exc.value)

    def test_leve_timeout_error_si_delai_depasse(self):
        import requests as req
        with patch("requests.get", side_effect=req.Timeout()):
            service = JiraService(_config_test())
            with pytest.raises(TimeoutError):
                service.get_ticket("KAN-4")

    def test_description_absente_retourne_message_par_defaut(self):
        data = _reponse_jira_valide()
        data["fields"]["description"] = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = data

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            ticket = service.get_ticket("KAN-4")

        assert ticket["description"] == "Aucune description."

    def test_assignee_absent_retourne_non_assigne(self):
        data = _reponse_jira_valide()
        data["fields"]["assignee"] = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = data

        with patch("requests.get", return_value=mock_response):
            service = JiraService(_config_test())
            ticket = service.get_ticket("KAN-4")

        assert "Non assign" in ticket["assignee"]


# ── JiraService.add_comment ───────────────────────────────────────────────────

class TestJiraServiceAddComment:

    def test_ajoute_commentaire_avec_succes(self):
        mock_response = MagicMock()
        mock_response.status_code = 201

        with patch("requests.post", return_value=mock_response):
            service = JiraService(_config_test())
            resultat = service.add_comment("KAN-4", "Implementation terminee.")

        assert resultat["succes"] is True
        assert resultat["ticket_id"] == "KAN-4"

    def test_leve_erreur_404_si_ticket_inexistant(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("requests.post", return_value=mock_response):
            service = JiraService(_config_test())
            with pytest.raises(FileNotFoundError):
                service.add_comment("KAN-999", "Commentaire")


# ── Format Markdown ───────────────────────────────────────────────────────────

class TestFormatTicketMarkdown:

    def test_format_contient_tous_les_champs(self):
        service = JiraService(_config_test())
        ticket = {
            "id": "KAN-4",
            "titre": "Ajouter un filtre",
            "statut": "To Do",
            "type": "Task",
            "priorite": "Medium",
            "projet": "Kanban",
            "assignee": "Wissal",
            "reporter": "Admin",
            "cree_le": "2026-08-10",
            "mis_a_jour_le": "2026-08-10",
            "labels": ["feature"],
            "description": "Description du ticket",
        }
        md = service.format_ticket_markdown(ticket)
        assert "KAN-4" in md
        assert "Ajouter un filtre" in md
        assert "To Do" in md
        assert "Medium" in md
        assert "Wissal" in md
        assert "Description du ticket" in md
        assert "feature" in md