"""
Indexe le code d'un Workspace dans une base vectorielle -- délègue à
CodebaseIndexerService. Construit l'EmbeddingProviderPort via la factory
partagée (jamais un fournisseur en dur), au moment de l'indexation,
jamais au démarrage.
"""

from llm.embedding_provider_factory import EmbeddingProviderConfigError, build_embedding_provider


class WorkspaceIndexerService:
    """Cas d'usage : indexer le code d'un Workspace, en lisant la clé API au moment de l'appel."""

    def __init__(self, credentials_store, provider_name: str = "gemini"):
        self._credentials_store = credentials_store
        self._provider_name = provider_name

    def index(self, repo_path: str, knowledge_base_path: str) -> str:
        """
        Indexe le code présent à repo_path, stocke le résultat à
        knowledge_base_path (jamais dans repo_path lui-même).
        """
        try:
            embedding_provider = build_embedding_provider(self._provider_name, self._credentials_store)
        except EmbeddingProviderConfigError as e:
            return str(e)

        from infra.simple_vector_store import SimpleJsonVectorStore
        from services.codebase_indexer_service import CodebaseIndexerService

        vector_store = SimpleJsonVectorStore(knowledge_base_path)
        indexeur = CodebaseIndexerService(embedding_provider, vector_store)

        return indexeur.index_project(repo_path)