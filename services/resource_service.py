"""
Service applicatif : orchestre le chargement de Resources en s'appuyant
UNIQUEMENT sur le port ResourceReaderPort (jamais sur MarkdownResourceLoader
directement) -- c'est ce qui permet de changer l'implémentation sans
toucher ce fichier.
"""

from typing import Dict, List

from core.entities.resource import Resource
from core.ports.resource_reader_port import ResourceReaderPort
from resources.resource_validator import ResourceValidator


class ResourceService:
    """Cas d'usage : charger une ou plusieurs Resources pour un projet donné."""

    def __init__(self, resource_reader: ResourceReaderPort, validator: ResourceValidator):
        # Injection de dépendances : ce service ne construit RIEN lui-même,
        # il reçoit ses dépendances de l'extérieur (via bootstrap.py plus tard).
        self._resource_reader = resource_reader
        self._validator = validator

    def load_resource(self, project_name: str, resource_name: str) -> Resource:
        """Charge une Resource unique et la valide."""
        contenu = self._resource_reader.read(project_name, resource_name)
        resource = Resource(project_name=project_name, name=resource_name, content=contenu)

        erreurs = self._validator.validate(resource)
        if erreurs:
            raise ValueError(f"Resource invalide : {'; '.join(erreurs)}")

        return resource

    def load_multiple(self, project_name: str, resource_names: List[str]) -> Dict[str, str]:
        """
        Charge plusieurs Resources d'un coup, renvoie un dict {nom: contenu}
        prêt à être passé à PromptTemplate.render().
        """
        resultat = {}
        for nom in resource_names:
            resource = self.load_resource(project_name, nom)
            resultat[nom] = resource.content
        return resultat

    def list_project_resources(self, project_name: str) -> List[str]:
        """Liste toutes les Resources disponibles pour un projet."""
        return self._resource_reader.list_available(project_name)