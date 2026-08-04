"""Vérifie WorkspaceIndexerService, avec un FakeCredentialsStore (aucun appel réseau réel)."""

from services.workspace_indexer_service import WorkspaceIndexerService


class FakeCredentialsStore:
    def __init__(self, valeurs: dict):
        self._valeurs = valeurs

    def get(self, key: str):
        return self._valeurs.get(key)


def test_index_refuse_sans_cle_api_configuree(tmp_path):
    service = WorkspaceIndexerService(FakeCredentialsStore({}))

    resultat = service.index(str(tmp_path / "repo"), str(tmp_path / "kb.json"))

    assert "GEMINI_API_KEY" in resultat


def test_index_refuse_un_fournisseur_inconnu(tmp_path):
    service = WorkspaceIndexerService(FakeCredentialsStore({"GEMINI_API_KEY": "x"}), provider_name="inconnu")

    resultat = service.index(str(tmp_path / "repo"), str(tmp_path / "kb.json"))

    assert "inconnu" in resultat


def test_index_lit_la_cle_au_moment_de_lappel_pas_a_la_construction(tmp_path):
    store = FakeCredentialsStore({})
    service = WorkspaceIndexerService(store)

    resultat_avant = service.index(str(tmp_path / "repo"), str(tmp_path / "kb.json"))
    assert "GEMINI_API_KEY" in resultat_avant

    store._valeurs["GEMINI_API_KEY"] = "fausse-cle-de-test"
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "example.py").write_text("def run(): pass")

    from unittest.mock import patch
    with patch("llm.gemini_embedding_provider.GeminiEmbeddingProvider.embed", return_value=[0.1, 0.2]):
        resultat_apres = service.index(str(tmp_path / "repo"), str(tmp_path / "kb.json"))

    assert "GEMINI_API_KEY" not in resultat_apres