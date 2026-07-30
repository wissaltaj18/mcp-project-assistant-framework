"""
Interface abstraite qu'un agent doit respecter. Aujourd'hui un seul
agent existe (CodeGenerationAgent), mais cette interface permet d'ajouter
demain un Code Review Agent, un Testing Agent, etc. sans rien casser.
"""

from abc import ABC, abstractmethod

from core.entities.generation_request import GenerationRequest


class BaseAgent(ABC):
    """Contrat qu'un agent doit respecter pour traiter une GenerationRequest."""

    @abstractmethod
    def handle(self, request: GenerationRequest) -> str:
        """Traite une demande de génération et renvoie le résultat."""
        raise NotImplementedError