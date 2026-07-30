"""
Point d'entrée du serveur MCP. Ce fichier ne fait QUE exposer des tools
MCP -- tout l'assemblage des dépendances est délégué à bootstrap.py.
"""

from mcp.server.fastmcp import FastMCP

from bootstrap import build_container
from core.entities.generation_request import GenerationRequest
from tools.file_tools import build_project_file_path, infer_output_path
from utils.string_utils import extract_code_block

mcp = FastMCP("mcp-project-assistant-framework")
_container = build_container()


@mcp.tool()
def read_project_resource(project_name: str, resource_name: str) -> str:
    """
    Lit une Resource (.md) d'un projet généré.

    Args:
        project_name: Nom du projet (ex: "aegisai")
        resource_name: Nom du fichier (ex: "business_rules.md")
    """
    try:
        resource = _container.resource_service.load_resource(project_name, resource_name)
        return resource.content
    except (FileNotFoundError, ValueError) as e:
        return f"Erreur : {e}"


@mcp.tool()
def list_project_resources(project_name: str) -> str:
    """Liste les Resources disponibles pour un projet."""
    disponibles = _container.resource_service.list_project_resources(project_name)
    if not disponibles:
        return f"Aucune resource trouvée pour le projet '{project_name}'."
    return "\n".join(disponibles)


@mcp.tool()
def list_available_prompts() -> str:
    """Liste les prompts de génération actuellement disponibles."""
    return "\n".join(_container.prompt_service.list_available_prompts())


@mcp.tool()
def generate_feature(project_name: str, prompt_name: str, page_name: str = "", output_path: str = "") -> str:
    """
    Génère du code pour une fonctionnalité via le LLM configuré, et
    l'écrit RÉELLEMENT sur le disque dans le projet généré.

    Args:
        project_name: Le projet cible (ex: "aegisai")
        prompt_name: Le prompt à utiliser (ex: "generate_login")
        page_name: Argument optionnel utilisé par certains prompts
        output_path: Chemin relatif où écrire (ex: "src/pages/login.html").
                     Si vide, déduit automatiquement de page_name.
    """
    request = GenerationRequest(
        project_name=project_name,
        prompt_name=prompt_name,
        arguments={"page_name": page_name} if page_name else {},
    )
    try:
        resultat_brut = _container.orchestrator.dispatch(request)
    except (ConnectionError, ValueError) as e:
        return f"Erreur : {e}"

    code = extract_code_block(resultat_brut)

    chemin_relatif = output_path or infer_output_path(prompt_name, page_name or prompt_name)
    chemin_complet = build_project_file_path(
        _container.settings.generated_projects_dir, project_name, chemin_relatif
    )

    _container.file_system.create_file(chemin_complet, code)

    return f"Fichier écrit : {chemin_complet} ({len(code)} caractères)"


if __name__ == "__main__":
    mcp.run(transport="stdio")