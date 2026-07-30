"""Utilitaires techniques purs pour manipuler des fichiers/dossiers."""

from pathlib import Path


def ensure_directory(path: str) -> None:
    """Crée un dossier (et ses parents) s'il n'existe pas déjà."""
    Path(path).mkdir(parents=True, exist_ok=True)


def safe_join(base: str, *parts: str) -> str:
    """
    Joint des segments de chemin en empêchant toute sortie du dossier `base`
    (protection basique contre les attaques de type path traversal via "..").
    """
    base_path = Path(base).resolve()
    joined = base_path.joinpath(*parts).resolve()
    if not str(joined).startswith(str(base_path)):
        raise ValueError(f"Chemin non autorisé (sort de '{base}') : {joined}")
    return str(joined)