"""
Agent séquentiel unique (aujourd'hui) : reçoit une demande, la délègue
à GenerationService. Simple par design -- toute la vraie logique vit
dans les services, l'agent ne fait qu'orchestrer au niveau le plus haut.
"""

from agents.base_agent import BaseAgent
from core.entities.generation_request import GenerationRequest
from services.generation_service import GenerationService


class CodeGenerationAgent(BaseAgent):
    """Agent qui gère les demandes de génération de code."""

    def __init__(self, generation_service: GenerationService):
        self._generation_service = generation_service

    def handle(self, request: GenerationRequest) -> str:
        return self._generation_service.generate(request)