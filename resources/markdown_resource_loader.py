"""
Implémentation concrète de ResourceReaderPort : lit de vrais fichiers .md
sur le disque, dans generated_projects/{project}/resources/.
"""

from pathlib import Path
from typing import List

from core.ports.resource_reader_port import ResourceReaderPort
from config.settings import FrameworkSettings
from utils.file_utils import safe_join


class MarkdownResourceLoader(ResourceReaderPort):
    """Charge les Resources .md depuis le système de fichiers local."""

    def __init__(self, settings: FrameworkSettings):
        self._settings = settings

    def read(self, project_name: str, resource_name: str) -> str:
        chemin_projet = Path(self._settings.generated_projects_dir) / project_name / "resources"
        chemin_complet = safe_join(str(chemin_projet), resource_name)

        fichier = Path(chemin_complet)
        if not fichier.exists():
            raise FileNotFoundError(
                f"Resource '{resource_name}' introuvable pour le projet '{project_name}' "
                f"(cherché dans {chemin_projet})"
            )
        return fichier.read_text(encoding="utf-8")

    def list_available(self, project_name: str) -> List[str]:
        chemin_projet = Path(self._settings.generated_projects_dir) / project_name / "resources"
        if not chemin_projet.exists():
            return []
        return sorted(f.name for f in chemin_projet.glob("*.md"))