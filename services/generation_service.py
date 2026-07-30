"""
Service applicatif central : orchestre une GenerationRequest de bout en
bout -- assembler le prompt (Resources incluses), l'envoyer au LLM,
renvoyer le résultat. C'est le coeur du "vibe coding" du framework.
"""

from core.entities.generation_request import GenerationRequest
from core.ports.llm_provider_port import LLMProviderPort
from core.ports.logger_port import LoggerPort
from services.prompt_service import PromptService


class GenerationService:
    """Cas d'usage central : exécute une GenerationRequest de bout en bout."""

    def __init__(
        self,
        prompt_service: PromptService,
        llm_provider: LLMProviderPort,
        logger: LoggerPort,
    ):
        self._prompt_service = prompt_service
        self._llm_provider = llm_provider
        self._logger = logger

    def generate(self, request: GenerationRequest) -> str:
        self._logger.info(f"Génération demandée : {request.describe()}")

        if not self._llm_provider.is_available():
            self._logger.error("LLM indisponible")
            raise ConnectionError(
                "Le LLM configuré n'est pas disponible. Vérifie qu'Ollama est lancé (ollama serve)."
            )

        prompt_final = self._prompt_service.build_prompt(
            request.project_name, request.prompt_name, **request.arguments
        )
        self._logger.info(f"Prompt assemblé ({len(prompt_final)} caractères), envoi au LLM...")

        resultat = self._llm_provider.generate(prompt_final)
        self._logger.info("Génération terminée")
        return resultat