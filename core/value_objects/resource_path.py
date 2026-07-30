"""Value object représentant le chemin logique d'une Resource."""

from dataclasses import dataclass

from core.value_objects.project_identifier import ProjectIdentifier


@dataclass(frozen=True)
class ResourcePath:
    """Combine un ProjectIdentifier et un nom de fichier .md de façon sûre."""

    project: ProjectIdentifier
    resource_name: str

    def __post_init__(self):
        if not self.resource_name.endswith(".md"):
            raise ValueError(f"Une Resource doit être un fichier .md : '{self.resource_name}'")
        if "/" in self.resource_name or ".." in self.resource_name:
            raise ValueError(f"Nom de Resource invalide (chemin non autorisé) : '{self.resource_name}'")

    def relative_path(self) -> str:
        return f"generated_projects/{self.project}/resources/{self.resource_name}"