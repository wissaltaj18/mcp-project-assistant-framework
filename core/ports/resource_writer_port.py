"""Port pour écrire une Resource sur disque -- séparé de la lecture (ResourceReaderPort existant)."""

from abc import ABC, abstractmethod


class ResourceWriterPort(ABC):
    """Contrat pour tout composant capable de persister le contenu d'une Resource."""

    @abstractmethod
    def write(self, directory_path: str, resource_name: str, content: str) -> None:
        """
        Écrit le contenu d'une Resource dans un dossier donné, en créant
        ce dossier si nécessaire.

        Args:
            directory_path: Dossier de destination (créé s'il n'existe pas)
            resource_name: Nom du fichier, ex: "technical_architecture.md"
            content: Contenu Markdown à écrire
        """
        raise NotImplementedError