"""
Service applicatif : assemble le texte final d'un prompt, en combinant
un PromptTemplate avec les Resources qu'il requiert pour un projet donné.
"""

from typing import Dict, List

from core.entities.prompt_template import PromptTemplate
from services.resource_service import ResourceService


class PromptNotFoundError(Exception):
    """Levée quand un prompt demandé n'existe pas dans le registre."""


class PromptService:
    """Cas d'usage : assembler le texte final d'un prompt pour un projet donné."""

    def __init__(self, resource_service: ResourceService, prompt_registry: Dict[str, PromptTemplate]):
        # prompt_registry est injecté de l'extérieur (construit dans bootstrap.py
        # à partir des fichiers de prompts/), pas construit ici.
        self._resource_service = resource_service
        self._prompt_registry = prompt_registry

    def build_prompt(self, project_name: str, prompt_name: str, **kwargs) -> str:
        template = self._prompt_registry.get(prompt_name)
        if template is None:
            disponibles = ", ".join(self._prompt_registry.keys())
            raise PromptNotFoundError(f"Prompt '{prompt_name}' introuvable. Disponibles : {disponibles}")

        resources_content = self._resource_service.load_multiple(
            project_name, template.required_resource_names
        )
        return template.render(resources_content, **kwargs)

    def list_available_prompts(self) -> List[str]:
        return list(self._prompt_registry.keys())
    
    def get_required_resources(self, prompt_name: str) -> List[str]:
        """Renvoie la liste des Resources qu'un prompt embarque, pour l'affichage."""
        template = self._prompt_registry.get(prompt_name)
        if template is None:
            raise PromptNotFoundError(f"Prompt '{prompt_name}' introuvable.")
        return template.required_resource_names