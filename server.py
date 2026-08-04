"""
Point d'entrée du serveur MCP. Ce fichier ne fait QUE exposer des tools
MCP -- tout l'assemblage des dépendances est délégué à bootstrap.py.
"""
import sys
_stdout_reel = sys.stdout
sys.stdout = sys.stderr  # neutralise tout print() egare pendant le demarrage
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from bootstrap import build_container
from core.entities.generation_request import GenerationRequest
from tools.file_tools import build_project_file_path, infer_output_path
from utils.string_utils import extract_code_block

from config import credentials_store
from infra.local_git_provider import LocalGitProvider
from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.chat_tools import ChatTools
from services.resource_generator_service import ResourceGeneratorService
from services.workspace_indexer_service import WorkspaceIndexerService
from services.workspace_service import WorkspaceService
from services.plan_storage_service import PlanStorageService
from services.plan_executor_service import PlanExecutorService

mcp = FastMCP("mcp-project-assistant-framework")
_container = build_container()

_WORKSPACES_DIR = str(Path(__file__).resolve().parent / "workspaces")

_workspace_service = WorkspaceService(LocalGitProvider(), _WORKSPACES_DIR)
_resource_generator = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
_workspace_indexer = WorkspaceIndexerService(credentials_store)
_chat_tools = ChatTools(
    _container,
    workspace_service=_workspace_service,
    resource_generator=_resource_generator,
    workspace_indexer=_workspace_indexer,
)

_dossier_plans_absolu = str(Path(__file__).resolve().parent / _chat_tools._chemin_projet_complet)
_plan_storage = PlanStorageService(_dossier_plans_absolu)
_plan_executor = PlanExecutorService(_container, _plan_storage, _chat_tools)


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


@mcp.tool()
def create_workspace(repo_url: str, branch: str = "", auth_token: str = "") -> str:
    """
    Crée un nouveau Workspace à partir d'un dépôt Git : clone le dépôt
    et prépare le terrain pour les futures analyses. Ne rend PAS ce
    Workspace actif automatiquement.

    Args:
        repo_url: URL du dépôt Git à importer
        branch: Branche spécifique à cloner (laisser vide pour la branche par défaut)
        auth_token: Token d'authentification pour un dépôt privé (optionnel)
    """
    return _chat_tools.create_workspace(repo_url, branch or None, auth_token or None)


@mcp.tool()
def set_active_workspace(workspace_id: str) -> str:
    """
    Active un Workspace déjà créé -- toutes les opérations suivantes
    (lecture, plans, RAG) porteront dessus.

    Args:
        workspace_id: Identifiant du Workspace, renvoyé par create_workspace
    """
    return _chat_tools.set_active_workspace(workspace_id)


@mcp.tool()
def generate_resources(workspace_id: str) -> str:
    """
    Génère les Resources (architecture technique, fonctionnelle, règles
    de développement) d'un Workspace, depuis son analyse d'architecture.

    Args:
        workspace_id: Identifiant du Workspace concerné
    """
    return _chat_tools.generate_resources(workspace_id)


@mcp.tool()
def index_workspace(workspace_id: str) -> str:
    """
    Indexe le code d'un Workspace dans sa base vectorielle (RAG).
    Nécessite un fournisseur d'embeddings configuré (Gemini par défaut).

    Args:
        workspace_id: Identifiant du Workspace concerné
    """
    return _chat_tools.index_workspace(workspace_id)


@mcp.tool()
def prepare_workspace(repo_url: str, branch: str = "", auth_token: str = "") -> str:
    """
    Workflow complet en un seul appel : clone le dépôt, crée et active
    le Workspace, génère ses Resources, l'indexe dans le RAG. Une fois
    terminé, tous les autres tools opèrent automatiquement sur ce
    Workspace.

    Args:
        repo_url: URL du dépôt Git à importer
        branch: Branche spécifique à cloner (optionnel)
        auth_token: Token d'authentification pour un dépôt privé (optionnel)
    """
    return _chat_tools.prepare_workspace(repo_url, branch or None, auth_token or None)


@mcp.tool()
def update_resource(workspace_id: str, resource_name: str, new_content: str) -> str:
    """
    Modifie une Resource existante d'un Workspace (ou en crée une nouvelle).

    Args:
        workspace_id: Identifiant du Workspace concerné
        resource_name: Nom du fichier, ex: development_rules.md
        new_content: Nouveau contenu complet de la Resource
    """
    return _chat_tools.update_resource(workspace_id, resource_name, new_content)


@mcp.tool()
def set_preference(workspace_id: str, key: str, value: str) -> str:
    """
    Définit une préférence de workflow pour un Workspace.

    Args:
        workspace_id: Identifiant du Workspace concerné
        key: Nom de la préférence, ex: run_tests_before_push
        value: Valeur de la préférence, ex: false
    """
    return _chat_tools.set_preference(workspace_id, key, value)


@mcp.tool()
def check_existing_feature(feature_name_hint: str) -> str:
    """Vérifie si une fonctionnalité liée existe DÉJÀ dans le code avant d'en proposer une nouvelle."""
    return _chat_tools.check_existing_feature(feature_name_hint)


@mcp.tool()
def read_file(file_path: str) -> str:
    """Lit le contenu réel d'un fichier du Workspace actif, sans le modifier."""
    return _chat_tools.read_file(file_path)


@mcp.tool()
def get_project_structure() -> str:
    """Renvoie l'arborescence réelle des fichiers de code du Workspace actif."""
    return _chat_tools.get_project_structure()


@mcp.tool()
def read_resource(resource_name: str) -> str:
    """Lit le contenu d'une Resource du Workspace actif (ex: development_rules.md)."""
    return _chat_tools.read_resource(resource_name)


@mcp.tool()
def find_project_file(file_name_hint: str) -> str:
    """Cherche un fichier du Workspace actif par son nom, quel que soit son type."""
    return _chat_tools.find_project_file(file_name_hint)


@mcp.tool()
def run_tests() -> str:
    """Exécute réellement la suite de tests du Workspace actif -- diagnostic, ne modifie rien."""
    return _chat_tools.run_tests()


@mcp.tool()
def create_plan(user_request: str, resources_consulted: list, duplication_check: str, steps: list) -> str:
    """
    SEULE façon de proposer une modification, un commit, ou un push.
    Calcule et fige le contenu exact de chaque étape, attend
    l'approbation de l'UTILISATEUR via approve_plan -- ne l'exécute
    JAMAIS toi-même. Appelle TOUJOURS check_existing_feature ET
    read_resource avant create_plan.

    Args:
        user_request: Résumé de la demande originale
        resources_consulted: Noms des Resources lues avant ce plan
        duplication_check: Résultat exact de check_existing_feature
        steps: Liste d'étapes (action_type, target, description, instruction, arguments)
    """
    return _chat_tools.create_plan(user_request, resources_consulted, duplication_check, steps)


@mcp.tool()
def approve_plan(plan_id: str) -> str:
    """
    APPROUVE et EXÉCUTE RÉELLEMENT un plan proposé par create_plan --
    c'est le SEUL moyen de déclencher une écriture, un commit, ou un
    push. Demande TOUJOURS une confirmation explicite de l'utilisateur
    avant d'appeler ce tool -- ne l'appelle jamais automatiquement juste
    après create_plan.

    Args:
        plan_id: Identifiant du plan, renvoyé par create_plan
    """
    resultat = _plan_executor.execute(plan_id, _chat_tools._project_name)
    return str(resultat)


@mcp.tool()
def reject_plan(plan_id: str) -> str:
    """
    Rejette un plan proposé -- aucune exécution n'a lieu.

    Args:
        plan_id: Identifiant du plan, renvoyé par create_plan
    """
    resultat = _plan_executor.reject(plan_id)
    return str(resultat)


@mcp.prompt()
def explain_architecture(workspace_id: str) -> str:
    """Explique l'architecture technique d'un Workspace, en s'appuyant sur les Resources déjà générées."""
    return (
        f"Active le Workspace '{workspace_id}', puis lis sa Resource technical_architecture.md. "
        f"Explique-moi clairement : les langages et framework utilisés, comment le projet est "
        f"structuré par couches (Controller/Service/Entity/Repository), et les dépendances principales."
    )


@mcp.prompt()
def review_code(workspace_id: str, file_path: str) -> str:
    """Relit un fichier en le confrontant aux règles de développement du Workspace."""
    return (
        f"Active le Workspace '{workspace_id}'. Lis d'abord sa Resource development_rules.md pour "
        f"connaître les conventions attendues (nommage, tests, linter). Puis lis le fichier "
        f"'{file_path}' et donne-moi un avis honnête : respecte-t-il ces conventions ? "
        f"Vois-tu des problèmes ou améliorations possibles ?"
    )


@mcp.prompt()
def check_before_implementing(workspace_id: str, feature_description: str) -> str:
    """Vérifie l'existant avant de proposer une nouvelle fonctionnalité."""
    return (
        f"Active le Workspace '{workspace_id}'. Avant toute chose, utilise check_existing_feature "
        f"pour vérifier si une fonctionnalité proche de celle-ci existe déjà : '{feature_description}'. "
        f"Lis aussi functional_overview.md pour comprendre le contexte métier. Ensuite seulement, "
        f"propose-moi un plan (via create_plan) pour : {feature_description}"
    )


@mcp.prompt()
def prepare_workspace_prompt(repo_url: str, branch: str = "", auth_token: str = "") -> str:
    """Prépare automatiquement un Workspace complet à partir d'un dépôt Git (privé ou public) : clone, analyse, Resources, RAG."""
    branche_txt = f" sur la branche {branch}" if branch else ""
    token_txt = f" avec le token d'authentification {auth_token}" if auth_token else ""
    return (
        f"Utilise le tool prepare_workspace pour préparer complètement le Workspace "
        f"à partir du dépôt {repo_url}{branche_txt}{token_txt}. Exécute-le entièrement, "
        f"sans me demander de confirmation intermédiaire, et donne-moi un seul message "
        f"récapitulatif à la fin."
    )


sys.stdout = _stdout_reel

if __name__ == "__main__":
    mcp.run(transport="stdio")