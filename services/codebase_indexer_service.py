"""
Service d'indexation : parcourt le codebase, découpe le code en fragments,
calcule leur embedding, et les stocke dans la base vectorielle -- la
Knowledge Base du framework.

Granularité : pour Python, découpage PAR FONCTION (via AST, précis). Pour
les autres langages (PHP, JS, Java...), découpage PAR FICHIER ENTIER --
moins précis, mais rend la recherche sémantique réellement utilisable sur
un projet non-Python, ce qui n'existait pas avant.
"""

from pathlib import Path

from core.ports.embedding_provider_port import EmbeddingProviderPort
from core.ports.vector_store_port import VectorStorePort
from services.code_search_service import PythonCodeSearchService

EXTENSIONS_AUTRES_LANGAGES = [".php", ".js", ".ts", ".java", ".cs", ".go", ".rb"]
TAILLE_MAX_FICHIER_INDEXE = 6000


class CodebaseIndexerService:
    """Cas d'usage : construire et maintenir la Knowledge Base du code d'un projet, tous langages."""

    def __init__(self, embedding_provider: EmbeddingProviderPort, vector_store: VectorStorePort):
        self._embeddings = embedding_provider
        self._vector_store = vector_store

    def index_project(self, project_root: str) -> str:
        """Indexe TOUT le projet depuis zéro, tous langages confondus."""
        racine = Path(project_root)
        if not racine.exists():
            return f"Projet introuvable : {project_root}"

        nb_fonctions_python = self._indexer_fonctions_python(racine, racine)
        nb_fichiers_autres = self._indexer_fichiers_autres_langages(racine, racine)

        return (
            f"{nb_fonctions_python} fonction(s) Python indexée(s) (granularité fine), "
            f"{nb_fichiers_autres} fichier(s) d'autres langages indexé(s) (granularité fichier entier)."
        )

    def reindex_file(self, project_root: str, file_relative_path: str) -> str:
        """Ré-indexe UN SEUL fichier (utilisé par l'indexation incrémentale Git)."""
        racine = Path(project_root)
        fichier = racine / file_relative_path

        self._vector_store.delete_by_file(file_relative_path)

        if not fichier.exists():
            return f"Fichier supprimé du projet, retiré de l'index : {file_relative_path}"

        if fichier.suffix == ".py":
            nb = self._indexer_une_fonction_python(fichier, racine)
            return f"{file_relative_path} ré-indexé : {nb} fonction(s)."

        if fichier.suffix in EXTENSIONS_AUTRES_LANGAGES:
            self._indexer_un_fichier_entier(fichier, racine)
            return f"{file_relative_path} ré-indexé (fichier entier, {fichier.suffix})."

        return f"Extension {fichier.suffix} non prise en charge pour l'indexation."

    def _indexer_fonctions_python(self, racine: Path, base: Path) -> int:
        nb_indexes = 0
        for fichier in racine.rglob("*.py"):
            nb_indexes += self._indexer_une_fonction_python(fichier, base)
        return nb_indexes

    def _indexer_une_fonction_python(self, fichier: Path, base: Path) -> int:
        import ast
        try:
            contenu = fichier.read_text(encoding="utf-8")
            arbre = ast.parse(contenu)
        except (SyntaxError, UnicodeDecodeError):
            return 0

        nb_indexes = 0
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.FunctionDef):
                source = ast.get_source_segment(contenu, noeud) or ""
                if not source.strip():
                    continue
                chemin_relatif = str(fichier.relative_to(base))
                chunk_id = f"{chemin_relatif}::{noeud.name}"
                texte_a_indexer = f"Fonction {noeud.name} dans {chemin_relatif} (Python) :\n{source}"
                vecteur = self._embeddings.embed(texte_a_indexer)
                self._vector_store.upsert(
                    chunk_id, vecteur,
                    {"file_path": chemin_relatif, "function_name": noeud.name, "code": source, "language": "Python"},
                )
                nb_indexes += 1
        return nb_indexes

    def _indexer_fichiers_autres_langages(self, racine: Path, base: Path) -> int:
        nb_indexes = 0
        for extension in EXTENSIONS_AUTRES_LANGAGES:
            for fichier in racine.rglob(f"*{extension}"):
                if self._indexer_un_fichier_entier(fichier, base):
                    nb_indexes += 1
        return nb_indexes

    def _indexer_un_fichier_entier(self, fichier: Path, base: Path) -> bool:
        try:
            contenu = fichier.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return False
        if not contenu.strip():
            return False

        contenu_tronque = contenu[:TAILLE_MAX_FICHIER_INDEXE]
        chemin_relatif = str(fichier.relative_to(base))
        chunk_id = f"{chemin_relatif}::fichier_entier"
        langage = fichier.suffix.lstrip(".")
        texte_a_indexer = f"Fichier {chemin_relatif} ({langage}) :\n{contenu_tronque}"

        vecteur = self._embeddings.embed(texte_a_indexer)
        self._vector_store.upsert(
            chunk_id, vecteur,
            {"file_path": chemin_relatif, "function_name": "(fichier entier)", "code": contenu_tronque, "language": langage},
        )
        return True