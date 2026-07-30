"""
Implémentation concrète de FileSystemPort : écrit/lit réellement des
fichiers sur le disque local. Plus la construction sécurisée du chemin
d'un fichier généré, pour empêcher toute sortie du dossier du projet.
"""

from pathlib import Path

from core.ports.file_system_port import FileSystemPort
from utils.file_utils import safe_join


class LocalFileSystem(FileSystemPort):
    """Écrit/lit réellement des fichiers sur le disque local."""

    def create_file(self, path: str, content: str) -> None:
        fichier = Path(path)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(content, encoding="utf-8")

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def file_exists(self, path: str) -> bool:
        return Path(path).exists()


def build_project_file_path(generated_projects_dir: str, project_name: str, relative_path: str) -> str:
    """
    Construit un chemin sûr pour écrire un fichier généré, empêchant toute
    sortie du dossier du projet (sécurité contre les chemins malveillants
    type "../../../etc/passwd" que le LLM pourrait générer par erreur).
    """
    base = f"{generated_projects_dir}/{project_name}"
    return safe_join(base, relative_path)

def infer_output_path(prompt_name: str, name: str) -> str:
    """
    Déduit un chemin relatif et une extension cohérents selon le type de
    prompt utilisé -- un backend s'écrit en .py, une page frontend en .html.
    """
    from utils.string_utils import slugify

    slug = slugify(name)
    if "backend" in prompt_name:
        return f"src/backend/{slug}.py"
    if "test" in prompt_name:
        return f"tests/generated/test_{slug}.py"
    return f"src/pages/{slug}.html"