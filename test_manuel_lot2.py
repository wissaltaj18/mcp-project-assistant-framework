from config.settings import FrameworkSettings
from resources.markdown_resource_loader import MarkdownResourceLoader
from resources.resource_validator import ResourceValidator
from services.resource_service import ResourceService

settings = FrameworkSettings.from_env()
loader = MarkdownResourceLoader(settings)
validator = ResourceValidator()
service = ResourceService(resource_reader=loader, validator=validator)

# Liste les resources disponibles pour aegisai
disponibles = service.list_project_resources("aegisai")
print("Resources disponibles :", disponibles)

# Charge la resource réelle
resource = service.load_resource("aegisai", "business_rules.md")
print("Contenu chargé :\n", resource.content)

# Vérifie qu'une resource inexistante lève bien une erreur claire
try:
    service.load_resource("aegisai", "inexistant.md")
except FileNotFoundError as e:
    print("OK, erreur bien gérée :", e)