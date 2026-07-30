"""
Stockage local des identifiants sensibles (clés API, tokens) -- permet à
l'utilisateur de les configurer UNE FOIS depuis l'interface (pas de
ligne de commande), persisté dans un fichier local jamais commité sur
Git (ajouté au .gitignore). Les fonctions get() vérifient d'abord ce
fichier, puis retombent sur les variables d'environnement (rétrocompatible
avec les tests/scripts existants).
"""

import json
import os
from pathlib import Path

_CHEMIN_FICHIER = Path(__file__).parent.parent / ".credentials.json"


def _charger() -> dict:
    if _CHEMIN_FICHIER.exists():
        return json.loads(_CHEMIN_FICHIER.read_text(encoding="utf-8"))
    return {}


def _sauvegarder(donnees: dict) -> None:
    _CHEMIN_FICHIER.write_text(json.dumps(donnees, indent=2), encoding="utf-8")


def get(key: str) -> str:
    """Renvoie l'identifiant stocké, ou la variable d'environnement du même nom en secours."""
    donnees = _charger()
    return donnees.get(key) or os.getenv(key, "")


def set_credential(key: str, value: str) -> None:
    """Stocke un identifiant de façon persistante, via l'interface (jamais un terminal)."""
    donnees = _charger()
    donnees[key] = value
    _sauvegarder(donnees)


def list_configured_keys() -> dict:
    """Renvoie quels identifiants sont configurés (juste un booléen, jamais la vraie valeur)."""
    donnees = _charger()
    cles_connues = ["GEMINI_API_KEY", "GITHUB_TOKEN", "ANTHROPIC_API_KEY"]
    return {cle: bool(donnees.get(cle) or os.getenv(cle)) for cle in cles_connues}