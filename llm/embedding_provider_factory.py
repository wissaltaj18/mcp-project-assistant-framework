"""
Point d'entrée UNIQUE pour construire un EmbeddingProviderPort dans tout
le projet -- utilisé à la fois par WorkspaceIndexerService et par
ChatTools (legacy). Aujourd'hui, seul "gemini" est implémenté ; ajouter
un futur fournisseur (OpenAI, local...) n'ajoute qu'un bloc ici, sans
toucher aux appelants.
"""


class EmbeddingProviderConfigError(Exception):
    """Levée quand la configuration nécessaire à un fournisseur d'embeddings est manquante ou invalide."""


def build_embedding_provider(provider_name: str, credentials_store):
    """
    Construit un EmbeddingProviderPort pour le fournisseur donné, en
    lisant sa configuration au moment de l'appel (jamais figée à un
    démarrage antérieur).

    Args:
        provider_name: Nom du fournisseur ("gemini" pour l'instant)
        credentials_store: Composant exposant .get(cle) pour lire les identifiants
    """
    if provider_name == "gemini":
        from llm.gemini_embedding_provider import GeminiEmbeddingProvider
        api_key = credentials_store.get("GEMINI_API_KEY")
        if not api_key:
            raise EmbeddingProviderConfigError(
                "La Knowledge Base nécessite GEMINI_API_KEY -- configure-la dans les Réglages avant d'indexer."
            )
        return GeminiEmbeddingProvider(api_key=api_key)

    raise EmbeddingProviderConfigError(f"Fournisseur d'embeddings inconnu : '{provider_name}'.")