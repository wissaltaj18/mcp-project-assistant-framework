"""Vérifie build_embedding_provider, sans appel réseau réel."""

import pytest

from llm.embedding_provider_factory import EmbeddingProviderConfigError, build_embedding_provider


class FakeCredentialsStore:
    def __init__(self, valeurs: dict):
        self._valeurs = valeurs

    def get(self, key: str):
        return self._valeurs.get(key)


def test_construit_gemini_avec_la_cle_configuree():
    store = FakeCredentialsStore({"GEMINI_API_KEY": "fausse-cle"})
    provider = build_embedding_provider("gemini", store)
    assert provider is not None


def test_refuse_gemini_sans_cle_configuree():
    store = FakeCredentialsStore({})
    with pytest.raises(EmbeddingProviderConfigError, match="GEMINI_API_KEY"):
        build_embedding_provider("gemini", store)


def test_refuse_un_fournisseur_inconnu():
    store = FakeCredentialsStore({"GEMINI_API_KEY": "fausse-cle"})
    with pytest.raises(EmbeddingProviderConfigError, match="inconnu"):
        build_embedding_provider("un-fournisseur-qui-nexiste-pas", store)