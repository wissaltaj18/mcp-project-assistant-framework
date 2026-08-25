"""
Composition Root : le SEUL fichier qui connait a la fois les interfaces
(core/ports/) et les implementations concretes (llm/, resources/, utils/).
Construit tous les objets une fois, au demarrage, et les assemble.
"""
from dataclasses import dataclass, field
from config.settings import FrameworkSettings
from config.llm_config import LLMConfig
from resources.markdown_resource_loader import MarkdownResourceLoader
from resources.resource_validator import ResourceValidator
from services.resource_service import ResourceService
from services.prompt_service import PromptService
from services.generation_service import GenerationService
from llm.llm_provider_factory import create_llm_provider
from tools.file_tools import LocalFileSystem
from agents.code_generation_agent import CodeGenerationAgent
from agents.agent_orchestrator import AgentOrchestrator
from utils.logging_utils import ConsoleLogger
from prompts.registry import build_prompt_registry


@dataclass
class Container:
    """Regroupe les services de haut niveau dont server.py et les scripts ont besoin."""
    settings: FrameworkSettings
    resource_service: ResourceService
    prompt_service: PromptService
    orchestrator: AgentOrchestrator
    file_system: LocalFileSystem
    generation_service: object = None


def build_container() -> Container:
    """Assemble toute la chaine de dependances (injection de dependances manuelle)."""
    settings = FrameworkSettings.from_env()
    llm_config = LLMConfig.from_env()
    logger = ConsoleLogger()
    resource_service = ResourceService(MarkdownResourceLoader(settings), ResourceValidator())
    prompt_registry = build_prompt_registry()
    prompt_service = PromptService(resource_service, prompt_registry)
    llm_provider = create_llm_provider(settings, llm_config)
    generation_service = GenerationService(prompt_service, llm_provider, logger)
    agent = CodeGenerationAgent(generation_service)
    orchestrator = AgentOrchestrator(agent)
    file_system = LocalFileSystem()
    return Container(
        settings=settings,
        resource_service=resource_service,
        prompt_service=prompt_service,
        orchestrator=orchestrator,
        file_system=file_system,
        generation_service=generation_service,
    )