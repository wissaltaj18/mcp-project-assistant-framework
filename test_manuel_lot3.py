from config.settings import FrameworkSettings
from resources.markdown_resource_loader import MarkdownResourceLoader
from resources.resource_validator import ResourceValidator
from services.resource_service import ResourceService
from services.prompt_service import PromptService, PromptNotFoundError
from services.generation_service import GenerationService
from agents.code_generation_agent import CodeGenerationAgent
from agents.agent_orchestrator import AgentOrchestrator
from core.entities.prompt_template import PromptTemplate
from core.entities.generation_request import GenerationRequest
from core.ports.llm_provider_port import LLMProviderPort
from utils.logging_utils import ConsoleLogger

settings = FrameworkSettings.from_env()
resource_service = ResourceService(MarkdownResourceLoader(settings), ResourceValidator())

registre_prompts = {
    "generate_login": PromptTemplate(
        name="generate_login",
        description="Génère la page de connexion",
        template_text="Génère la page {page_name} en respectant les règles métier ci-dessous.",
        required_resource_names=["business_rules.md"],
    )
}
prompt_service = PromptService(resource_service, registre_prompts)

# Un FAUX LLM pour tester sans avoir besoin qu'Ollama tourne
class FakeLLMProvider(LLMProviderPort):
    def generate(self, prompt, max_tokens=1000):
        return f"CODE GÉNÉRÉ pour: {prompt[:40]}..."
    def is_available(self):
        return True

logger = ConsoleLogger()
generation_service = GenerationService(prompt_service, FakeLLMProvider(), logger)
agent = CodeGenerationAgent(generation_service)
orchestrator = AgentOrchestrator(agent)

request = GenerationRequest(project_name="aegisai", prompt_name="generate_login", arguments={"page_name": "Login"})
resultat = orchestrator.dispatch(request)
print("\n=== RÉSULTAT FINAL ===")
print(resultat)