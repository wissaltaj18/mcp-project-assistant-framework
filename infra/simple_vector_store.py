"""
Implémentation concrète de VectorStorePort : simple, sans dépendance
externe lourde (pas de serveur ChromaDB à installer/gérer), stockée dans
un fichier JSON, recherche par similarité cosinus en pur Python. Adaptée
à un projet de démonstration (quelques centaines de fragments) -- pas
pensée pour des millions de vecteurs, mais fonctionnellement correcte.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.ports.vector_store_port import VectorStorePort


def _similarite_cosinus(a: List[float], b: List[float]) -> float:
    produit_scalaire = sum(x * y for x, y in zip(a, b))
    norme_a = math.sqrt(sum(x * x for x in a))
    norme_b = math.sqrt(sum(y * y for y in b))
    if norme_a == 0 or norme_b == 0:
        return 0.0
    return produit_scalaire / (norme_a * norme_b)


class SimpleJsonVectorStore(VectorStorePort):
    """Base vectorielle persistée dans un simple fichier JSON."""

    def __init__(self, chemin_fichier: str):
        self._chemin = Path(chemin_fichier)
        self._donnees: Dict[str, dict] = {}
        self._charger()

    def _charger(self) -> None:
        if self._chemin.exists():
            self._donnees = json.loads(self._chemin.read_text(encoding="utf-8"))

    def _sauvegarder(self) -> None:
        self._chemin.parent.mkdir(parents=True, exist_ok=True)
        self._chemin.write_text(json.dumps(self._donnees, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, chunk_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self._donnees[chunk_id] = {"vector": vector, "metadata": metadata}
        self._sauvegarder()

    def delete(self, chunk_id: str) -> None:
        if chunk_id in self._donnees:
            del self._donnees[chunk_id]
            self._sauvegarder()

    def delete_by_file(self, file_path: str) -> None:
        a_supprimer = [
            cid for cid, entree in self._donnees.items()
            if entree["metadata"].get("file_path") == file_path
        ]
        for cid in a_supprimer:
            del self._donnees[cid]
        if a_supprimer:
            self._sauvegarder()

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        resultats = []
        for chunk_id, entree in self._donnees.items():
            score = _similarite_cosinus(query_vector, entree["vector"])
            resultats.append((chunk_id, score, entree["metadata"]))
        resultats.sort(key=lambda r: r[1], reverse=True)
        return resultats[:top_k]

    def count(self) -> int:
        return len(self._donnees)