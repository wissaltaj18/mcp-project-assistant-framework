"""
Service applicatif : recherche sémantique dans la Knowledge Base -- prend
une question en langage naturel, la transforme en vecteur, retrouve les
fragments de code les plus pertinents.
"""

from core.ports.embedding_provider_port import EmbeddingProviderPort
from core.ports.vector_store_port import VectorStorePort


class KnowledgeBaseService:
    """Cas d'usage : recherche sémantique de code par similarité de sens."""

    def __init__(self, embedding_provider: EmbeddingProviderPort, vector_store: VectorStorePort):
        self._embeddings = embedding_provider
        self._vector_store = vector_store

    def search(self, query: str, top_k: int = 3) -> str:
        if self._vector_store.count() == 0:
            return "La Knowledge Base est vide. Utilise index_project d'abord."

        vecteur_requete = self._embeddings.embed(query)
        resultats = self._vector_store.search(vecteur_requete, top_k=top_k)

        if not resultats:
            return "Aucun résultat pertinent trouvé."

        lignes = ["Fragments de code les plus pertinents trouvés :"]
        for chunk_id, score, metadata in resultats:
            lignes.append(
                f"- {metadata['function_name']} dans {metadata['file_path']} "
                f"(pertinence {score:.2f})"
            )
        return "\n".join(lignes)