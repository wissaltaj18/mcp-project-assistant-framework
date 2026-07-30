"""
Service applicatif qui orchestre l'indexation incrémentale : compare le
commit Git actuel avec celui du dernier indexage, ne ré-indexe QUE les
fichiers réellement modifiés -- pas tout le projet à chaque fois.
"""

import json
from pathlib import Path

from core.ports.git_port import GitPort
from services.codebase_indexer_service import CodebaseIndexerService


class IncrementalIndexingService:
    """Cas d'usage : maintenir la Knowledge Base à jour au fil des commits Git."""

    def __init__(self, git_provider: GitPort, indexer: CodebaseIndexerService):
        self._git = git_provider
        self._indexer = indexer

    def _chemin_etat(self, project_root: str) -> Path:
        return Path(project_root) / ".index_state.json"

    def _lire_dernier_hash(self, project_root: str) -> "str | None":
        chemin = self._chemin_etat(project_root)
        if not chemin.exists():
            return None
        return json.loads(chemin.read_text(encoding="utf-8")).get("last_indexed_commit")

    def _ecrire_dernier_hash(self, project_root: str, commit_hash: str) -> None:
        self._chemin_etat(project_root).write_text(
            json.dumps({"last_indexed_commit": commit_hash}), encoding="utf-8"
        )

    def reindex_incremental(self, project_root: str) -> str:
        """
        Ré-indexe uniquement les fichiers modifiés depuis le dernier
        indexage (détecté via Git). Si aucun indexage précédent, ou si ce
        n'est pas un dépôt Git, fait un indexage complet.
        """
        hash_actuel = self._git.get_current_commit_hash(project_root)

        if hash_actuel is None:
            return self._indexer.index_project(project_root) + " (pas de suivi Git détecté)"

        dernier_hash = self._lire_dernier_hash(project_root)

        if dernier_hash is None:
            resultat = self._indexer.index_project(project_root)
            self._ecrire_dernier_hash(project_root, hash_actuel)
            return resultat + " (premier indexage complet)"

        if dernier_hash == hash_actuel:
            return "Aucun changement détecté depuis le dernier indexage, Knowledge Base déjà à jour."

        fichiers_changes = self._git.get_changed_files_since(project_root, dernier_hash)
        if not fichiers_changes:
            self._ecrire_dernier_hash(project_root, hash_actuel)
            return "Commits détectés mais aucun fichier Python changé."

        for fichier in fichiers_changes:
            self._indexer.reindex_file(project_root, fichier)

        self._ecrire_dernier_hash(project_root, hash_actuel)
        return f"Indexation incrémentale : {len(fichiers_changes)} fichier(s) ré-indexé(s) : {', '.join(fichiers_changes)}."