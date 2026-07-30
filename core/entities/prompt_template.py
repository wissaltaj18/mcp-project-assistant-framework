"""Entité représentant un Prompt générique du framework."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class PromptTemplate:
    """
    Un Prompt générique (ex: generate_backend), avec la liste des noms
    de Resources qu'il doit systématiquement embarquer, quel que soit
    le projet actif.
    """

    name: str
    description: str
    template_text: str
    required_resource_names: List[str] = field(default_factory=list)

    def render(self, resources_content: dict[str, str], **kwargs) -> str:
        """
        Assemble le texte final : instruction + resources embarquées.

        Args:
            resources_content: dict {nom_resource: contenu} déjà chargé
            kwargs: arguments à injecter dans le template (ex: feature_name)
        """
        instruction = self.template_text.format(**kwargs)
        morceaux = [instruction]
        for nom in self.required_resource_names:
            contenu = resources_content.get(nom, f"[Resource '{nom}' introuvable]")
            morceaux.append(f"\n--- {nom} ---\n{contenu}")
        return "\n".join(morceaux)