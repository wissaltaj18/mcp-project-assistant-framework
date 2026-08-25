"""
Tests Sprint 33 : get_attachments + download_attachment dans JiraService
+ tool download_jira_attachment
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from config.jira_config import JiraConfig
from services.jira_service import JiraService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config():
    return JiraConfig(
        base_url="https://wissaltestmcp.atlassian.net",
        email="test@example.com",
        api_token="fake-token",
    )


def _service():
    return JiraService(_config())


def _attachments():
    return [
        {
            "id": "1",
            "filename": "tv.jpg",
            "content_url": "https://jira/attach/tv.jpg",
            "mime_type": "image/jpeg",
            "size": 102400
        }
    ]


def tool_download_jira_attachment(
    ticket_id: str,
    filename: str,
    dest_dir: str,
    jira_service,
) -> str:
    if jira_service is None:
        return "Jira non configure."
    if not ticket_id.strip():
        return "Erreur : ticket_id est vide."
    if not filename.strip():
        return "Erreur : filename est vide."
    try:
        attachments = jira_service.get_attachments(ticket_id)
        if not attachments:
            return f"Aucune piece jointe trouvee sur le ticket {ticket_id}."

        target = next(
            (a for a in attachments if a["filename"].lower() == filename.lower()),
            None
        )
        if target is None:
            noms = [a["filename"] for a in attachments]
            return (
                f"Fichier '{filename}' non trouve sur {ticket_id}. "
                f"Pieces jointes disponibles : {', '.join(noms)}"
            )

        dest_path = str(Path(dest_dir) / target["filename"])
        resultat = jira_service.download_attachment(target["content_url"], dest_path)
        return (
            f"Image '{target['filename']}' telechargee avec succes.\n"
            f"Chemin : {resultat['dest_path']}\n"
            f"Taille : {resultat['size']} octets"
        )
    except FileNotFoundError as e:
        return f"Ticket ou piece jointe introuvable : {e}"
    except PermissionError as e:
        return f"Erreur authentification : {e}"
    except (ConnectionError, TimeoutError) as e:
        return f"Erreur reseau : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


# ── Tests get_attachments ──────────────────────────────────────────────────────

class TestGetAttachments:

    def _mock_response(self, attachments):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {
            "fields": {"attachment": attachments}
        }
        return mock

    def test_retourne_liste_attachments(self):
        mock_resp = self._mock_response([
            {"id": "1", "filename": "tv.jpg",
             "content": "https://jira/attach/tv.jpg",
             "mimeType": "image/jpeg", "size": 102400}
        ])
        with patch("requests.get", return_value=mock_resp):
            result = _service().get_attachments("KAN-6")

        assert len(result) == 1
        assert result[0]["filename"] == "tv.jpg"
        assert result[0]["mime_type"] == "image/jpeg"
        assert result[0]["content_url"] == "https://jira/attach/tv.jpg"

    def test_retourne_liste_vide_si_aucun_attachment(self):
        mock_resp = self._mock_response([])
        with patch("requests.get", return_value=mock_resp):
            result = _service().get_attachments("KAN-6")
        assert result == []

    def test_retourne_plusieurs_attachments(self):
        mock_resp = self._mock_response([
            {"id": "1", "filename": "tv.jpg", "content": "url1",
             "mimeType": "image/jpeg", "size": 1024},
            {"id": "2", "filename": "spec.pdf", "content": "url2",
             "mimeType": "application/pdf", "size": 2048},
        ])
        with patch("requests.get", return_value=mock_resp):
            result = _service().get_attachments("KAN-6")
        assert len(result) == 2
        noms = [a["filename"] for a in result]
        assert "tv.jpg" in noms
        assert "spec.pdf" in noms

    def test_leve_erreur_404_ticket_introuvable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(FileNotFoundError) as exc:
                _service().get_attachments("KAN-999")
        assert "KAN-999" in str(exc.value)

    def test_leve_erreur_401_auth_invalide(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(PermissionError):
                _service().get_attachments("KAN-6")

    def test_leve_connection_error(self):
        import requests as req
        with patch("requests.get", side_effect=req.ConnectionError()):
            with pytest.raises(ConnectionError):
                _service().get_attachments("KAN-6")


# ── Tests download_attachment ─────────────────────────────────────────────────

class TestDownloadAttachment:

    def test_telecharge_fichier_avec_succes(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [b"fake image data"]

        dest = str(tmp_path / "tv.jpg")
        with patch("requests.get", return_value=mock_resp):
            result = _service().download_attachment(
                "https://jira/attach/tv.jpg", dest
            )

        assert result["succes"] is True
        assert result["dest_path"] == dest
        assert Path(dest).exists()

    def test_cree_dossier_parent_si_absent(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [b"data"]

        dest = str(tmp_path / "sous_dossier" / "tv.jpg")
        with patch("requests.get", return_value=mock_resp):
            _service().download_attachment("https://jira/attach/tv.jpg", dest)

        assert Path(dest).exists()

    def test_leve_erreur_401(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(PermissionError):
                _service().download_attachment(
                    "https://jira/attach/tv.jpg", "/tmp/tv.jpg"
                )

    def test_leve_erreur_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(FileNotFoundError):
                _service().download_attachment(
                    "https://jira/attach/tv.jpg", "/tmp/tv.jpg"
                )


# ── Tests tool_download_jira_attachment ───────────────────────────────────────

class TestToolDownloadJiraAttachment:

    def test_retourne_erreur_si_jira_non_configure(self):
        result = tool_download_jira_attachment("KAN-6", "tv.jpg", "/tmp", None)
        assert "non configur" in result.lower()

    def test_retourne_erreur_si_ticket_id_vide(self):
        result = tool_download_jira_attachment("", "tv.jpg", "/tmp", _service())
        assert "vide" in result.lower()

    def test_retourne_erreur_si_filename_vide(self):
        result = tool_download_jira_attachment("KAN-6", "", "/tmp", _service())
        assert "vide" in result.lower()

    def test_retourne_erreur_si_aucun_attachment(self):
        service = _service()
        with patch.object(service, 'get_attachments', return_value=[]):
            result = tool_download_jira_attachment("KAN-6", "tv.jpg", "/tmp", service)
        assert "aucune" in result.lower()

    def test_retourne_erreur_si_fichier_non_trouve(self):
        service = _service()
        with patch.object(service, 'get_attachments', return_value=_attachments()):
            result = tool_download_jira_attachment(
                "KAN-6", "autre.jpg", "/tmp", service
            )
        assert "non trouve" in result.lower()
        assert "tv.jpg" in result

    def test_telecharge_avec_succes(self, tmp_path):
        service = _service()
        with patch.object(service, 'get_attachments', return_value=_attachments()), \
             patch.object(service, 'download_attachment', return_value={
                 "succes": True,
                 "dest_path": str(tmp_path / "tv.jpg"),
                 "size": 102400
             }):
            result = tool_download_jira_attachment(
                "KAN-6", "tv.jpg", str(tmp_path), service
            )
        assert "succes" in result.lower()
        assert "tv.jpg" in result

    def test_insensible_a_la_casse_du_nom_fichier(self, tmp_path):
        service = _service()
        with patch.object(service, 'get_attachments', return_value=_attachments()), \
             patch.object(service, 'download_attachment', return_value={
                 "succes": True,
                 "dest_path": str(tmp_path / "tv.jpg"),
                 "size": 102400
             }):
            result = tool_download_jira_attachment(
                "KAN-6", "TV.JPG", str(tmp_path), service
            )
        assert "succes" in result.lower()