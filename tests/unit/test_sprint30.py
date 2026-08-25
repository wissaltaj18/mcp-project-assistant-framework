"""
Tests Sprint 30 : SonarConfig + SonarService
Aucun appel réseau réel -- tout est mocké via unittest.mock.patch.
"""

import pytest
from unittest.mock import patch, MagicMock
from config.sonar_config import SonarConfig
from services.sonar_service import SonarService


# ── SonarConfig ───────────────────────────────────────────────────────────────

class TestSonarConfig:

    def test_charge_depuis_env(self, monkeypatch):
        monkeypatch.setenv("SONAR_TOKEN", "mon-token-sonar")
        monkeypatch.setenv("SONAR_ORGANIZATION", "wissaltaj18")
        monkeypatch.setenv("SONAR_PROJECT_KEY", "wissaltaj18_E-commerce")
        config = SonarConfig.from_env()
        assert config.token == "mon-token-sonar"
        assert config.organization == "wissaltaj18"
        assert config.project_key == "wissaltaj18_E-commerce"
        assert config.base_url == "https://sonarcloud.io"

    def test_base_url_par_defaut(self, monkeypatch):
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.setenv("SONAR_ORGANIZATION", "org")
        monkeypatch.setenv("SONAR_PROJECT_KEY", "key")
        monkeypatch.delenv("SONAR_BASE_URL", raising=False)
        config = SonarConfig.from_env()
        assert config.base_url == "https://sonarcloud.io"

    def test_leve_erreur_si_token_manquant(self, monkeypatch):
        monkeypatch.delenv("SONAR_TOKEN", raising=False)
        monkeypatch.setenv("SONAR_ORGANIZATION", "wissaltaj18")
        monkeypatch.setenv("SONAR_PROJECT_KEY", "wissaltaj18_E-commerce")
        with pytest.raises(ValueError) as exc:
            SonarConfig.from_env()
        assert "SONAR_TOKEN" in str(exc.value)

    def test_leve_erreur_si_organization_manquante(self, monkeypatch):
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.delenv("SONAR_ORGANIZATION", raising=False)
        monkeypatch.setenv("SONAR_PROJECT_KEY", "key")
        with pytest.raises(ValueError) as exc:
            SonarConfig.from_env()
        assert "SONAR_ORGANIZATION" in str(exc.value)

    def test_leve_erreur_si_project_key_manquant(self, monkeypatch):
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.setenv("SONAR_ORGANIZATION", "org")
        monkeypatch.delenv("SONAR_PROJECT_KEY", raising=False)
        with pytest.raises(ValueError) as exc:
            SonarConfig.from_env()
        assert "SONAR_PROJECT_KEY" in str(exc.value)

    def test_message_erreur_liste_toutes_les_variables_manquantes(self, monkeypatch):
        monkeypatch.delenv("SONAR_TOKEN", raising=False)
        monkeypatch.delenv("SONAR_ORGANIZATION", raising=False)
        monkeypatch.delenv("SONAR_PROJECT_KEY", raising=False)
        with pytest.raises(ValueError) as exc:
            SonarConfig.from_env()
        msg = str(exc.value)
        assert "SONAR_TOKEN" in msg
        assert "SONAR_ORGANIZATION" in msg
        assert "SONAR_PROJECT_KEY" in msg

    def test_is_configured_retourne_true(self, monkeypatch):
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.setenv("SONAR_ORGANIZATION", "org")
        monkeypatch.setenv("SONAR_PROJECT_KEY", "key")
        config = SonarConfig(base_url="x", token="x", organization="x", project_key="x")
        assert config.is_configured() is True

    def test_is_configured_retourne_false_si_token_manquant(self, monkeypatch):
        monkeypatch.delenv("SONAR_TOKEN", raising=False)
        monkeypatch.setenv("SONAR_ORGANIZATION", "org")
        monkeypatch.setenv("SONAR_PROJECT_KEY", "key")
        config = SonarConfig(base_url="x", token="x", organization="x", project_key="x")
        assert config.is_configured() is False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config():
    return SonarConfig(
        base_url="https://sonarcloud.io",
        token="fake-token",
        organization="wissaltaj18",
        project_key="wissaltaj18_E-commerce",
    )


def _service():
    return SonarService(_config())


def _reponse_measures():
    return {
        "component": {
            "key": "wissaltaj18_E-commerce",
            "measures": [
                {"metric": "bugs", "value": "2"},
                {"metric": "vulnerabilities", "value": "0"},
                {"metric": "code_smells", "value": "15"},
                {"metric": "coverage", "value": "45.3"},
                {"metric": "duplicated_lines_density", "value": "3.2"},
                {"metric": "reliability_rating", "value": "2"},
                {"metric": "security_rating", "value": "1"},
                {"metric": "sqale_rating", "value": "1"},
                {"metric": "alert_status", "value": "OK"},
            ]
        }
    }


def _reponse_quality_gate():
    return {
        "projectStatus": {
            "status": "OK",
            "conditions": [
                {"metricKey": "bugs", "status": "OK", "actualValue": "2", "errorThreshold": "10"},
                {"metricKey": "coverage", "status": "ERROR", "actualValue": "45.3", "errorThreshold": "80.0"},
            ]
        }
    }


# ── SonarService.get_measures ─────────────────────────────────────────────────

class TestGetMeasures:

    def test_retourne_metriques_parsees(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _reponse_measures()

        with patch("requests.get", return_value=mock_resp):
            measures = _service().get_measures()

        assert measures["bugs"] == "2"
        assert measures["vulnerabilities"] == "0"
        assert measures["coverage"] == "45.3"
        assert measures["security_rating"] == "1"

    def test_leve_erreur_401_token_invalide(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(PermissionError) as exc:
                _service().get_measures()
        assert "SONAR_TOKEN" in str(exc.value)

    def test_leve_erreur_404_projet_introuvable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(FileNotFoundError) as exc:
                _service().get_measures()
        assert "wissaltaj18_E-commerce" in str(exc.value)

    def test_leve_connection_error(self):
        import requests as req
        with patch("requests.get", side_effect=req.ConnectionError()):
            with pytest.raises(ConnectionError):
                _service().get_measures()

    def test_leve_timeout_error(self):
        import requests as req
        with patch("requests.get", side_effect=req.Timeout()):
            with pytest.raises(TimeoutError):
                _service().get_measures()

    def test_retourne_dict_vide_si_aucune_mesure(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"component": {"measures": []}}

        with patch("requests.get", return_value=mock_resp):
            measures = _service().get_measures()

        assert measures == {}


# ── SonarService.get_quality_gate ─────────────────────────────────────────────

class TestGetQualityGate:

    def test_retourne_statut_pass(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _reponse_quality_gate()

        with patch("requests.get", return_value=mock_resp):
            qg = _service().get_quality_gate()

        assert qg["statut"] == "PASS"
        assert len(qg["conditions"]) == 2

    def test_retourne_statut_fail(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "projectStatus": {"status": "ERROR", "conditions": []}
        }

        with patch("requests.get", return_value=mock_resp):
            qg = _service().get_quality_gate()

        assert qg["statut"] == "FAIL"

    def test_conditions_parsees_correctement(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _reponse_quality_gate()

        with patch("requests.get", return_value=mock_resp):
            qg = _service().get_quality_gate()

        bugs = next(c for c in qg["conditions"] if c["metrique"] == "bugs")
        assert bugs["statut"] == "PASS"
        assert bugs["valeur_actuelle"] == "2"

        coverage = next(c for c in qg["conditions"] if c["metrique"] == "coverage")
        assert coverage["statut"] == "FAIL"

    def test_leve_erreur_401_token_invalide(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(PermissionError):
                _service().get_quality_gate()

    def test_leve_erreur_404_projet_introuvable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(FileNotFoundError):
                _service().get_quality_gate()


# ── Format Markdown ───────────────────────────────────────────────────────────

class TestFormatReportMarkdown:

    def test_contient_quality_gate_pass(self):
        measures = {
            "bugs": "0", "vulnerabilities": "0", "code_smells": "5",
            "coverage": "82.0", "duplicated_lines_density": "1.2",
            "reliability_rating": "1", "security_rating": "1", "sqale_rating": "1"
        }
        quality_gate = {"statut": "PASS", "conditions": []}
        rapport = _service().format_report_markdown(measures, quality_gate)
        assert "PASS" in rapport
        assert "wissaltaj18_E-commerce" in rapport
        assert "82.0%" in rapport

    def test_contient_quality_gate_fail(self):
        measures = {"bugs": "5", "coverage": "30.0"}
        quality_gate = {
            "statut": "FAIL",
            "conditions": [
                {"metrique": "bugs", "statut": "FAIL", "valeur_actuelle": "5", "seuil": "0"}
            ]
        }
        rapport = _service().format_report_markdown(measures, quality_gate)
        assert "FAIL" in rapport
        assert "corrections" in rapport.lower()

    def test_rating_converti_en_lettre(self):
        measures = {
            "reliability_rating": "1",
            "security_rating": "2",
            "sqale_rating": "3"
        }
        quality_gate = {"statut": "PASS", "conditions": []}
        rapport = _service().format_report_markdown(measures, quality_gate)
        assert "A" in rapport
        assert "B" in rapport
        assert "C" in rapport

    def test_contient_section_conditions(self):
        measures = {}
        quality_gate = {
            "statut": "FAIL",
            "conditions": [
                {"metrique": "coverage", "statut": "FAIL",
                 "valeur_actuelle": "45.0", "seuil": "80.0"}
            ]
        }
        rapport = _service().format_report_markdown(measures, quality_gate)
        assert "coverage" in rapport
        assert "45.0" in rapport
        assert "80.0" in rapport