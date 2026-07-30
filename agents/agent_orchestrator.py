"""
Coordonne un ou plusieurs agents. Aujourd'hui : un seul agent enregistré,
appelé directement. Demain : pourra router vers plusieurs agents
spécialisés selon le type de demande, sans changer les couches supérieures.
"""

from agents.base_agent import BaseAgent
from core.entities.generation_request import GenerationRequest


class AgentOrchestrator:
    """Point d'entrée unique pour dispatcher une demande vers le bon agent."""

    def __init__(self, default_agent: BaseAgent):
        self._default_agent = default_agent

    def dispatch(self, request: GenerationRequest) -> str:
        return self._default_agent.handle(request)