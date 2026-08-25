from dotenv import load_dotenv
load_dotenv()
"""
Point d'entrée du serveur MCP. Ce fichier ne fait QUE exposer des tools
MCP -- tout l'assemblage des dépendances est délégué à bootstrap.py.
"""
import sys
_stdout_reel = sys.stdout
sys.stdout = sys.stderr

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
from services.knowledge_base_loader import KnowledgeBaseLoader
from services.git_service import GitService
from config.jira_config import JiraConfig
from services.jira_service import JiraService
from config.sonar_config import SonarConfig
from services.sonar_service import SonarService
from prompts_sprint28 import prompt_implement_from_jira_ticket, tool_add_jira_comment
from prompts_sprint31 import prompt_jira_workflow

import tempfile
import os

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

_kb_loader = KnowledgeBaseLoader(_workspace_service)
_dossier_plans_absolu = str(Path(__file__).resolve().parent / _chat_tools._chemin_projet_complet)
_plan_storage = PlanStorageService(_dossier_plans_absolu)
_plan_executor = PlanExecutorService(_container, _plan_storage, _chat_tools)

# Jira -- optionnel
try:
    _jira_config = JiraConfig.from_env()
    _jira_service = JiraService(_jira_config)
except ValueError:
    _jira_config = None
    _jira_service = None

# SonarCloud -- optionnel
try:
    _sonar_config = SonarConfig.from_env()
    _sonar_service = SonarService(_sonar_config)
except ValueError:
    _sonar_config = None
    _sonar_service = None


def _ws_file() -> str:
    """Chemin du fichier de persistance du Workspace actif."""
    return os.path.join(tempfile.gettempdir(), "mcp_active_workspace.txt")


def _restaurer_workspace_si_necessaire():
    """Restaure le Workspace actif depuis le fichier de persistance si necessaire."""
    if not _chat_tools._active_workspace_id:
        ws_file = _ws_file()
        if os.path.exists(ws_file):
            try:
                workspace_id = open(ws_file, encoding="utf-8").read().strip()
                if workspace_id:
                    _chat_tools.set_active_workspace(workspace_id)
            except Exception:
                pass


# ── Tools Workspace ───────────────────────────────────────────────────────────

@mcp.tool()
def read_project_resource(project_name: str, resource_name: str) -> str:
    """Lit une Resource (.md) d'un projet généré."""
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
    """Génère du code pour une fonctionnalité via le LLM configuré."""
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
    """Crée un nouveau Workspace à partir d'un dépôt Git."""
    return _chat_tools.create_workspace(repo_url, branch or None, auth_token or None)


@mcp.tool()
def set_active_workspace(workspace_id: str) -> str:
    """Active un Workspace déjà créé."""
    resultat = _chat_tools.set_active_workspace(workspace_id)
    # Persister le workspace actif dans un fichier temp
    try:
        open(_ws_file(), "w", encoding="utf-8").write(workspace_id)
    except Exception:
        pass
    return resultat


@mcp.tool()
def generate_resources(workspace_id: str) -> str:
    """Génère les Resources d'un Workspace depuis son analyse d'architecture."""
    return _chat_tools.generate_resources(workspace_id)


@mcp.tool()
def index_workspace(workspace_id: str) -> str:
    """Indexe le code d'un Workspace dans sa base vectorielle (RAG)."""
    return _chat_tools.index_workspace(workspace_id)


@mcp.tool()
def prepare_workspace(repo_url: str, branch: str = "", auth_token: str = "") -> str:
    """Workflow complet : clone, active, génère les Resources, indexe."""
    return _chat_tools.prepare_workspace(repo_url, branch or None, auth_token or None)


@mcp.tool()
def update_resource(workspace_id: str, resource_name: str, new_content: str) -> str:
    """Modifie une Resource existante d'un Workspace."""
    return _chat_tools.update_resource(workspace_id, resource_name, new_content)


@mcp.tool()
def set_preference(workspace_id: str, key: str, value: str) -> str:
    """Définit une préférence de workflow pour un Workspace."""
    return _chat_tools.set_preference(workspace_id, key, value)


@mcp.tool()
def check_existing_feature(feature_name_hint: str) -> str:
    """Vérifie si une fonctionnalité liée existe DÉJÀ dans le code."""
    _restaurer_workspace_si_necessaire()
    return _chat_tools.check_existing_feature(feature_name_hint)


@mcp.tool()
def read_file(file_path: str) -> str:
    """Lit le contenu réel d'un fichier du Workspace actif."""
    _restaurer_workspace_si_necessaire()
    return _chat_tools.read_file(file_path)


@mcp.tool()
def get_project_structure() -> str:
    """Renvoie l'arborescence réelle des fichiers du Workspace actif."""
    _restaurer_workspace_si_necessaire()
    return _chat_tools.get_project_structure()


@mcp.tool()
def read_resource(resource_name: str) -> str:
    """Lit le contenu d'une Resource du Workspace actif."""
    _restaurer_workspace_si_necessaire()
    return _chat_tools.read_resource(resource_name)


@mcp.tool()
def find_project_file(file_name_hint: str) -> str:
    """Cherche un fichier du Workspace actif par son nom."""
    _restaurer_workspace_si_necessaire()
    return _chat_tools.find_project_file(file_name_hint)


@mcp.tool()
def run_tests() -> str:
    """Exécute réellement la suite de tests du Workspace actif."""
    _restaurer_workspace_si_necessaire()
    return _chat_tools.run_tests()


@mcp.tool()
def create_plan(user_request: str, resources_consulted: list, duplication_check: str, steps: list) -> str:
    """
    SEULE façon de proposer une modification. Calcule et fige le contenu
    exact de chaque étape, attend l'approbation via approve_plan.
    """
    _restaurer_workspace_si_necessaire()
    return _chat_tools.create_plan(user_request, resources_consulted, duplication_check, steps)


@mcp.tool()
def approve_plan(plan_id: str) -> str:
    """APPROUVE et EXÉCUTE RÉELLEMENT un plan proposé par create_plan."""
    _restaurer_workspace_si_necessaire()
    if not _chat_tools._active_workspace_id:
        return "Erreur : aucun Workspace actif. Appelle set_active_workspace d'abord."
    from services.plan_storage_service import PlanStorageService
    from services.plan_executor_service import PlanExecutorService
    storage = PlanStorageService(_chat_tools._chemin_projet_complet)
    executor = PlanExecutorService(_container, storage, _chat_tools)
    resultat = executor.execute(plan_id, _chat_tools._project_name)
    return str(resultat)


@mcp.tool()
def reject_plan(plan_id: str) -> str:
    """Rejette un plan proposé -- aucune exécution n'a lieu."""
    resultat = _plan_executor.reject(plan_id)
    return str(resultat)


# ── Tools Jira ────────────────────────────────────────────────────────────────

@mcp.tool()
def read_jira_ticket(ticket_id: str) -> str:
    """Lit un ticket Jira et retourne son contenu complet."""
    if _jira_service is None:
        return (
            "Jira non configuré. Ajoute ces variables dans ton fichier .env :\n"
            "  JIRA_BASE_URL=https://ton-org.atlassian.net\n"
            "  JIRA_EMAIL=ton-email@example.com\n"
            "  JIRA_API_TOKEN=ton-token-jira"
        )
    try:
        ticket = _jira_service.get_ticket(ticket_id)
        return _jira_service.format_ticket_markdown(ticket)
    except FileNotFoundError as e:
        return f"Ticket introuvable : {e}"
    except PermissionError as e:
        return f"Erreur d'authentification : {e}"
    except ConnectionError as e:
        return f"Erreur réseau : {e}"
    except TimeoutError as e:
        return f"Timeout : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


@mcp.tool()
def add_jira_comment(ticket_id: str, comment: str) -> str:
    """Ajoute un commentaire sur un ticket Jira."""
    return tool_add_jira_comment(ticket_id, comment, _jira_service)


@mcp.tool()
def update_jira_status(ticket_id: str, status: str) -> str:
    """Change le statut d'un ticket Jira (ex: 'En cours', 'Terminé')."""
    if _jira_service is None:
        return "Jira non configuré."
    if not ticket_id or not ticket_id.strip():
        return "Erreur : ticket_id est vide."
    if not status or not status.strip():
        return "Erreur : le statut demandé est vide."
    try:
        resultat = _jira_service.update_status(ticket_id.strip(), status.strip())
        return (
            f"Statut du ticket {resultat['ticket_id']} mis à jour avec succès : "
            f"{resultat['nouveau_statut']}."
        )
    except FileNotFoundError:
        return f"Ticket '{ticket_id}' introuvable sur Jira."
    except PermissionError as e:
        return f"Erreur d'authentification Jira : {e}"
    except ValueError as e:
        return f"Erreur de transition : {e}"
    except (ConnectionError, TimeoutError) as e:
        return f"Erreur réseau Jira : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


@mcp.tool()
def download_jira_attachment(ticket_id: str, filename: str, workspace_id: str) -> str:
    """Télécharge une pièce jointe d'un ticket Jira dans le dossier public/ du Workspace."""
    if _jira_service is None:
        return "Jira non configuré."
    if not ticket_id.strip():
        return "Erreur : ticket_id est vide."
    if not filename.strip():
        return "Erreur : filename est vide."
    _restaurer_workspace_si_necessaire()
    try:
        attachments = _jira_service.get_attachments(ticket_id)
        if not attachments:
            return f"Aucune pièce jointe trouvée sur le ticket {ticket_id}."
        target = next(
            (a for a in attachments if a["filename"].lower() == filename.lower()),
            None
        )
        if target is None:
            noms = [a["filename"] for a in attachments]
            return (
                f"Fichier '{filename}' non trouvé sur {ticket_id}. "
                f"Pièces jointes disponibles : {', '.join(noms)}"
            )
        dest_dir = Path(_chat_tools._chemin_projet_complet) / "public"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = str(dest_dir / target["filename"])
        resultat = _jira_service.download_attachment(target["content_url"], dest_path)
        return (
            f"Image '{target['filename']}' téléchargée dans public/.\n"
            f"Chemin : {resultat['dest_path']}\n"
            f"Taille : {resultat['size']} octets"
        )
    except FileNotFoundError as e:
        return f"Ticket ou pièce jointe introuvable : {e}"
    except PermissionError as e:
        return f"Erreur authentification : {e}"
    except (ConnectionError, TimeoutError) as e:
        return f"Erreur réseau : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


# ── Tools SonarCloud ──────────────────────────────────────────────────────────

@mcp.tool()
def get_sonar_report(workspace_id: str) -> str:
    """Récupère le rapport SonarCloud : Quality Gate, bugs, vulnérabilités, couverture."""
    if _sonar_service is None:
        return (
            "SonarCloud non configuré. Ajoute ces variables dans ton .env :\n"
            "  SONAR_TOKEN=ton-token-sonarcloud\n"
            "  SONAR_ORGANIZATION=wissaltaj18\n"
            "  SONAR_PROJECT_KEY=wissaltaj18_E-commerce"
        )
    try:
        measures = _sonar_service.get_measures()
        quality_gate = _sonar_service.get_quality_gate()
        return _sonar_service.format_report_markdown(measures, quality_gate)
    except FileNotFoundError as e:
        return f"Projet SonarCloud introuvable : {e}"
    except PermissionError as e:
        return f"Erreur d'authentification SonarCloud : {e}"
    except ConnectionError as e:
        return f"Erreur réseau SonarCloud : {e}"
    except TimeoutError as e:
        return f"Timeout SonarCloud : {e}"
    except Exception as e:
        return f"Erreur inattendue SonarCloud : {e}"


# ── Tools Git ─────────────────────────────────────────────────────────────────

@mcp.tool()
def sync_workspace(workspace_id: str) -> str:
    """Synchronise le Workspace avec GitHub via git pull."""
    _restaurer_workspace_si_necessaire()
    if _chat_tools._git_service is None:
        _chat_tools._git_service = GitService(_chat_tools._chemin_projet_complet)
    git = _chat_tools._git_service
    if not git.is_git_repo():
        return "Le Workspace actif n'est pas un dépôt Git valide."
    try:
        status = git.get_status()
        if not status["is_clean"]:
            fichiers = status["modified"] + status["staged"]
            return (
                f"Synchronisation impossible : modifications locales non committées.\n"
                f"Fichiers concernés : {', '.join(fichiers)}."
            )
        resultat = git.pull()
        if resultat["deja_a_jour"]:
            return "Workspace déjà à jour avec GitHub."
        return f"Workspace synchronisé. Fichiers mis à jour : {len(resultat['fichiers_mis_a_jour'])}"
    except RuntimeError as e:
        return f"Erreur Git : {e}"
    except TimeoutError as e:
        return f"Timeout Git : {e}"
    except Exception as e:
        return f"Erreur inattendue : {e}"


@mcp.tool()
def get_git_diff(workspace_id: str) -> str:
    """Retourne le résumé des fichiers modifiés dans le dernier commit."""
    _restaurer_workspace_si_necessaire()
    if _chat_tools._git_service is None:
        _chat_tools._git_service = GitService(_chat_tools._chemin_projet_complet)
    try:
        diff = _chat_tools._git_service.get_diff_summary()
        if not diff["fichiers"]:
            return "Aucune modification détectée dans le dernier commit."
        return f"Fichiers modifiés :\n{diff['resume']}"
    except Exception as e:
        return f"Erreur lors de la récupération du diff : {e}"


# ── Prompts ───────────────────────────────────────────────────────────────────

@mcp.prompt()
def setup_workspace(repo_url: str, branch: str = "", auth_token: str = "") -> str:
    """Prépare un Workspace complet à partir d'un dépôt Git."""
    branche_txt = f" sur la branche {branch}" if branch else ""
    token_txt = f" avec le token d'authentification {auth_token}" if auth_token else ""
    return (
        f"Utilise le tool prepare_workspace pour préparer complètement le Workspace "
        f"à partir du dépôt {repo_url}{branche_txt}{token_txt}. Exécute-le entièrement, "
        f"sans me demander de confirmation intermédiaire, et donne-moi un seul message "
        f"récapitulatif à la fin."
    )


@mcp.prompt()
def implement_feature(workspace_id: str, feature_description: str) -> str:
    """Implémente une fonctionnalité en chargeant toute la Knowledge Base."""
    _restaurer_workspace_si_necessaire()
    kb = _kb_loader.load_context(workspace_id)
    return (
        f"Tu es un ingénieur senior sur ce projet.\n\n"
        f"{kb}\n\n"
        f"---\n\n"
        f"## MISSION\n"
        f"Implémenter : **{feature_description}**\n\n"
        f"## PROCESSUS OBLIGATOIRE\n"
        f"1. `check_existing_feature` pour vérifier qu'une fonctionnalité similaire n'existe pas.\n"
        f"2. `get_project_structure` pour localiser les fichiers concernés.\n"
        f"3. Respecte les CONSTRAINTS de la Knowledge Base.\n"
        f"4. Propose un plan via `create_plan` -- NE MODIFIE JAMAIS sans approbation.\n"
        f"5. Attends l'accord explicite de l'utilisateur."
    )


@mcp.prompt()
def review_code(workspace_id: str, file_path: str) -> str:
    """Review d'un fichier selon les standards réels du projet."""
    kb = _kb_loader.load_context(
        workspace_id,
        sections=["development_rules.md", "review_checklist.md", "security_rules.md"]
    )
    return (
        f"Tu es un ingénieur senior qui effectue une code review stricte.\n\n"
        f"{kb}\n\n"
        f"## FICHIER À REVIEWER\n`{file_path}`\n\n"
        f"Lis d'abord le fichier avec `read_file`, puis structure ta review en 4 sections :\n"
        f"### 1. VIOLATIONS CRITIQUES\n### 2. RISQUES DE SÉCURITÉ\n"
        f"### 3. SUGGESTIONS D'AMÉLIORATION\n### 4. VERDICT\n"
        f"✅ Approuvé / ⚠️ Approuvé avec réserves / ❌ Refusé"
    )


@mcp.prompt()
def fix_bug(workspace_id: str, bug_description: str) -> str:
    """Diagnostique et corrige un bug."""
    kb = _kb_loader.load_context(
        workspace_id,
        sections=["technical_architecture.md", "functional_overview.md", "development_rules.md"]
    )
    return (
        f"Tu es un ingénieur senior en charge du debugging.\n\n"
        f"{kb}\n\n"
        f"## BUG RAPPORTÉ\n{bug_description}\n\n"
        f"## PROCESSUS\n"
        f"1. `get_project_structure` pour cartographier les fichiers.\n"
        f"2. `read_file` pour lire les fichiers suspects.\n"
        f"3. Propose un fix via `create_plan`."
    )


@mcp.prompt()
def security_review(workspace_id: str) -> str:
    """Audit de sécurité complet."""
    kb = _kb_loader.load_context(
        workspace_id,
        sections=["security_rules.md", "engineering_principles.md"]
    )
    return (
        f"Tu es un ingénieur sécurité senior.\n\n{kb}\n\n"
        f"## MISSION\nEffectuer un audit de sécurité complet.\n\n"
        f"## POINTS À VÉRIFIER\n"
        f"1. Gestion des secrets\n2. Validation des entrées\n"
        f"3. Protection CSRF\n4. Injections SQL\n"
        f"5. Exposition d'informations sensibles\n6. Dépendances vulnérables"
    )


@mcp.prompt()
def onboard_project(workspace_id: str) -> str:
    """Guide d'onboarding complet pour un nouveau développeur."""
    kb = _kb_loader.load_context(workspace_id)
    return (
        f"Tu es un tech lead qui accueille un nouveau développeur.\n\n{kb}\n\n"
        f"## MISSION\nGénère un guide d'onboarding complet.\n\n"
        f"## STRUCTURE\n"
        f"1. Vue d'ensemble\n2. Architecture\n3. Vocabulaire métier\n"
        f"4. Règles non négociables\n5. Processus de développement\n6. Pièges courants"
    )


@mcp.prompt()
def refactor(workspace_id: str, target_description: str) -> str:
    """Refactoring guidé par la philosophie d'architecture du projet."""
    kb = _kb_loader.load_context(
        workspace_id,
        sections=["engineering_principles.md", "technical_architecture.md", "development_rules.md"]
    )
    return (
        f"Tu es un ingénieur senior en charge d'un refactoring.\n\n{kb}\n\n"
        f"## CIBLE\n{target_description}\n\n"
        f"## PROCESSUS\n"
        f"1. `read_file` pour lire le code cible.\n"
        f"2. Identifie les ANTI-PATTERNS.\n"
        f"3. Propose un plan via `create_plan`.\n"
        f"4. Attends l'approbation."
    )


@mcp.prompt()
def explain_architecture(workspace_id: str) -> str:
    """Explique l'architecture du projet."""
    kb = _kb_loader.load_context(
        workspace_id,
        sections=["technical_architecture.md", "functional_overview.md"]
    )
    return (
        f"Tu es un ingénieur senior qui explique l'architecture.\n\n{kb}\n\n"
        f"## MISSION\nExplique :\n"
        f"1. Langages et frameworks\n2. Structure par couches\n"
        f"3. Patterns architecturaux\n4. Dépendances principales\n5. Entités métier"
    )


@mcp.prompt()
def implement_from_jira_ticket(workspace_id: str, ticket_id: str) -> str:
    """Implémente un ticket Jira en chargeant la Knowledge Base."""
    return prompt_implement_from_jira_ticket(
        workspace_id, ticket_id, _jira_service, _kb_loader
    )


@mcp.prompt()
def sonar_report(workspace_id: str) -> str:
    """Génère un rapport qualité SonarCloud complet."""
    return (
        f"Utilise `get_sonar_report` avec workspace_id='{workspace_id}'.\n"
        f"Présente : Quality Gate, bugs, vulnérabilités, couverture, notes, recommandations."
    )


@mcp.prompt()
def jira_workflow(workspace_id: str, ticket_id: str) -> str:
    """Workflow Jira complet : lit le ticket, implémente, analyse SonarCloud, clôture."""
    _restaurer_workspace_si_necessaire()
    return prompt_jira_workflow(
        workspace_id, ticket_id, _jira_service, _sonar_service, _kb_loader
    )


sys.stdout = _stdout_reel

if __name__ == "__main__":
    mcp.run(transport="stdio")