"""Implémentation concrète de ResourceWriterPort : écrit un fichier Markdown sur disque local."""

from pathlib import Path

from core.ports.resource_writer_port import ResourceWriterPort


class MarkdownResourceWriter(ResourceWriterPort):
    """Écrit une Resource comme un simple fichier .md sur le système de fichiers local."""

    def write(self, directory_path: str, resource_name: str, content: str) -> None:
        dossier = Path(directory_path)
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / resource_name).write_text(content, encoding="utf-8")