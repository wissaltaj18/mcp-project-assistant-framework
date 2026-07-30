from core.entities.resource import Resource
from core.entities.prompt_template import PromptTemplate
from core.entities.tool_definition import ToolDefinition
from core.entities.generation_request import GenerationRequest
from core.value_objects.project_identifier import ProjectIdentifier
from core.value_objects.resource_path import ResourcePath
from config.settings import FrameworkSettings
from config.llm_config import LLMConfig
from utils.logging_utils import ConsoleLogger
from utils.string_utils import slugify, truncate

# Resource
r = Resource(project_name="aegisai", name="business_rules.md", content="Règle X")
print("Resource OK :", r)

# PromptTemplate
pt = PromptTemplate(
    name="generate_login",
    description="Génère la page login",
    template_text="Génère la page {page_name}.",
    required_resource_names=["business_rules.md"],
)
print("Prompt rendu :\n", pt.render({"business_rules.md": "Contenu"}, page_name="Login"))

# ProjectIdentifier -- doit accepter un nom valide
pid = ProjectIdentifier("aegisai")
print("ProjectIdentifier OK :", pid)

# ProjectIdentifier -- doit REFUSER un nom invalide
try:
    ProjectIdentifier("Ae Gis !!")
    print("PROBLÈME : aurait dû refuser ce nom")
except ValueError as e:
    print("ProjectIdentifier refuse bien un nom invalide :", e)

# Config
print("Settings :", FrameworkSettings.from_env())
print("LLM Config :", LLMConfig.from_env())

# Logger
ConsoleLogger().info("Le lot 1 fonctionne")