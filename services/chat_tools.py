"""
Les outils exposés à l'agent conversationnel. Ce sont de simples fonctions
Python -- chaque provider (Gemini/Ollama/Claude) génère automatiquement
leur schéma depuis TOOL_SCHEMAS (services/tool_schemas.py).

RÈGLE DE SÉCURITÉ STRUCTURELLE : le LLM n'a accès à AUCUN tool qui modifie
un fichier, écrit en base de données, crée un commit, un push, ou une
pull request -- directement. Sa SEULE capacité d'écriture est create_plan,
qui ne fait que PROPOSER (calcule et fige le contenu exact, mais n'écrit
rien). Seul un clic utilisateur dans l'interface, via l'endpoint HTTP
/api/v1/plans/{id}/approve (jamais vu par le LLM), déclenche l'exécution
réelle via PlanExecutorService.
"""

import uuid

from services.workspace_service import WorkspaceAlreadyExistsError
from services.workspace_indexer_service import WorkspaceIndexerService
from services.code_search_service import PythonCodeSearchService
from tools.file_tools import build_project_file_path
from utils.string_utils import extract_code_block

from core.entities.workspace import WorkspaceStatus

class ChatTools:
    """Regroupe les actions qu'un agent conversationnel peut décider d'exécuter."""

    def __init__(
        self, container, project_name: str = "aegisai", repo_path: "str | None" = None, *,
        workspace_service, resource_generator, workspace_indexer, embedding_provider_name: str = "gemini",
    ):
        self._c = container
        self._project_name = project_name
        self._workspace_service = workspace_service
        self._resource_generator = resource_generator
        self._workspace_indexer = workspace_indexer
        self._embedding_provider_name = embedding_provider_name
        self._active_workspace_id = None  # None = mode legacy (project_name), sinon = Workspace actif
        self._git_service = None
        if repo_path is not None:
            chemin_projet = repo_path
        else:
            chemin_projet = f"{container.settings.generated_projects_dir}/{project_name}"
        self._code_search = PythonCodeSearchService(chemin_projet)
        self._chemin_projet_complet = chemin_projet
        self._knowledge_base_service = None
        self._incremental_indexing_service = None
        self._database = None
        self._plan_storage = None
        self._audit_logger = None

    def _resoudre_chemin_knowledge_base(self) -> str:
        if self._active_workspace_id is not None:
            return self._workspace_service.get_knowledge_base_path(self._active_workspace_id)
        return f"{self._chemin_projet_complet}/.knowledge_base.json"

    def _get_knowledge_base_service(self):
        if self._knowledge_base_service is None:
            from config import credentials_store
            from llm.embedding_provider_factory import build_embedding_provider
            from infra.simple_vector_store import SimpleJsonVectorStore
            from services.knowledge_base_service import KnowledgeBaseService

            embedding_provider = build_embedding_provider(self._embedding_provider_name, credentials_store)
            vector_store = SimpleJsonVectorStore(self._resoudre_chemin_knowledge_base())
            self._knowledge_base_service = KnowledgeBaseService(embedding_provider, vector_store)
        return self._knowledge_base_service

    def _get_incremental_indexing_service(self):
        if self._incremental_indexing_service is None:
            from config import credentials_store
            from llm.embedding_provider_factory import build_embedding_provider
            from infra.simple_vector_store import SimpleJsonVectorStore
            from infra.local_git_provider import LocalGitProvider
            from services.codebase_indexer_service import CodebaseIndexerService
            from services.incremental_indexing_service import IncrementalIndexingService

            embedding_provider = build_embedding_provider(self._embedding_provider_name, credentials_store)
            vector_store = SimpleJsonVectorStore(f"{self._chemin_projet_complet}/.knowledge_base.json")
            indexeur = CodebaseIndexerService(embedding_provider, vector_store)
            self._incremental_indexing_service = IncrementalIndexingService(LocalGitProvider(), indexeur)
        return self._incremental_indexing_service

    def _get_database(self):
        if self._database is None:
            from infra.sqlite_database_provider import SqliteDatabaseProvider
            self._database = SqliteDatabaseProvider(f"{self._chemin_projet_complet}/app_data.sqlite3")
        return self._database

    def _get_plan_storage(self):
        if self._plan_storage is None:
            from services.plan_storage_service import PlanStorageService
            self._plan_storage = PlanStorageService(self._chemin_projet_complet)
        return self._plan_storage

    def _get_audit_logger(self):
        if self._audit_logger is None:
            from infra.jsonl_audit_logger import JsonlAuditLogger
            self._audit_logger = JsonlAuditLogger(self._chemin_projet_complet)
        return self._audit_logger

    def create_workspace(self, repo_url: str, branch: "str | None" = None, auth_token: "str | None" = None) -> str:
        try:
           workspace = self._workspace_service.create_workspace(repo_url, branch, auth_token)
        except WorkspaceAlreadyExistsError as e:
            return str(e)
        if workspace.status.value == "error":
            return f"Échec de la création du Workspace '{workspace.workspace_id}' : {workspace.error_message}"
        return (
            f"Workspace '{workspace.workspace_id}' créé avec succès (statut : {workspace.status.value}). "
            f"Ce Workspace n'est pas encore actif -- l'utilisateur doit le sélectionner explicitement."
        )

    def set_active_workspace(self, workspace_id: str) -> str:
        workspace = self._workspace_service.get_workspace(workspace_id)
        if workspace is None:
            return f"Workspace '{workspace_id}' introuvable. Utilise create_workspace pour en créer un."
        if workspace.status.value == "error":
            return f"Impossible d'activer '{workspace_id}' : ce Workspace est en erreur ({workspace.error_message})."

        self._chemin_projet_complet = self._workspace_service.get_repo_path(workspace_id)
        self._code_search = PythonCodeSearchService(self._chemin_projet_complet)
        self._knowledge_base_service = None
        self._incremental_indexing_service = None
        self._database = None
        self._plan_storage = None
        self._audit_logger = None
        self._active_workspace_id = workspace_id
        from services.git_service import GitService
        self._git_service = GitService(self._chemin_projet_complet)

        return f"Workspace '{workspace_id}' activé (statut : {workspace.status.value}). Toutes les actions suivantes porteront sur ce Workspace."

    def generate_resources(self, workspace_id: str) -> str:
        workspace = self._workspace_service.get_workspace(workspace_id)
        if workspace is None:
            return f"Workspace '{workspace_id}' introuvable. Utilise create_workspace pour en créer un."
        if workspace.status.value == "error":
            return f"Impossible de générer les Resources de '{workspace_id}' : ce Workspace est en erreur ({workspace.error_message})."

        repo_path = self._workspace_service.get_repo_path(workspace_id)
        resources_path = self._workspace_service.get_resources_path(workspace_id)
        resultats = self._resource_generator.generate_all(repo_path, resources_path)

        # Sprint 26 : passer le statut a READY apres generation reussie
        if workspace.status.value == "analyzing":
            workspace.status = WorkspaceStatus.READY
            self._workspace_service.save_preferences(workspace_id, self._workspace_service.get_preferences(workspace_id))

        noms_fichiers = ", ".join(resultats.keys())
        return f"Resources générées pour '{workspace_id}' : {noms_fichiers} (dans {resources_path})."

    def update_resource(self, workspace_id: str, resource_name: str, new_content: str) -> str:
        workspace = self._workspace_service.get_workspace(workspace_id)
        if workspace is None:
            return f"Workspace '{workspace_id}' introuvable. Utilise create_workspace pour en créer un."
        if workspace.status.value == "error":
            return f"Impossible de modifier une Resource de '{workspace_id}' : ce Workspace est en erreur ({workspace.error_message})."

        resources_path = self._workspace_service.get_resources_path(workspace_id)
        self._resource_generator.update_resource(resources_path, resource_name, new_content)
        return f"Resource '{resource_name}' mise à jour pour le Workspace '{workspace_id}'."

    def set_preference(self, workspace_id: str, key: str, value: str) -> str:
        workspace = self._workspace_service.get_workspace(workspace_id)
        if workspace is None:
            return f"Workspace '{workspace_id}' introuvable. Utilise create_workspace pour en créer un."
        if workspace.status.value == "error":
            return f"Impossible de définir une préférence pour '{workspace_id}' : ce Workspace est en erreur ({workspace.error_message})."

        preferences = self._workspace_service.get_preferences(workspace_id)
        preferences.set(key, value)
        self._workspace_service.save_preferences(workspace_id, preferences)
        return f"Préférence '{key}' = '{value}' enregistrée pour le Workspace '{workspace_id}'."

    def index_workspace(self, workspace_id: str) -> str:
        workspace = self._workspace_service.get_workspace(workspace_id)
        if workspace is None:
            return f"Workspace '{workspace_id}' introuvable. Utilise create_workspace pour en créer un."
        if workspace.status.value == "error":
            return f"Impossible d'indexer '{workspace_id}' : ce Workspace est en erreur ({workspace.error_message})."

        repo_path = self._workspace_service.get_repo_path(workspace_id)
        knowledge_base_path = self._workspace_service.get_knowledge_base_path(workspace_id)
        return self._workspace_indexer.index(repo_path, knowledge_base_path)

    def prepare_workspace(self, repo_url: str, branch: "str | None" = None, auth_token: "str | None" = None) -> str:
        resultat_creation = self.create_workspace(repo_url, branch, auth_token)
        if "créé avec succès" not in resultat_creation:
            return f"Préparation interrompue à la création du Workspace : {resultat_creation}"

        workspace = self._workspace_service.get_workspace(self._deriver_slug_pour_verification(repo_url))
        workspace_id = workspace.workspace_id if workspace else None
        if workspace_id is None:
            return f"Préparation interrompue : impossible de retrouver le Workspace après sa création. {resultat_creation}"

        resultat_activation = self.set_active_workspace(workspace_id)
        if "activé" not in resultat_activation:
            return f"Préparation interrompue à l'activation : {resultat_activation}"

        resultat_resources = self.generate_resources(workspace_id)
        resultat_index = self.index_workspace(workspace_id)

        return (
            f"Workspace '{workspace_id}' entièrement préparé et actif :\n"
            f"1. Création : OK\n"
            f"2. Activation : OK\n"
            f"3. Resources : {resultat_resources}\n"
            f"4. Indexation : {resultat_index}\n"
            f"Tous les tools suivants opèrent maintenant sur ce Workspace."
        )

    def _deriver_slug_pour_verification(self, repo_url: str) -> str:
        import re
        nom_brut = re.sub(r"\.git$", "", repo_url.rstrip("/").split("/")[-1])
        slug = nom_brut.lower()
        return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")

    def import_external_repository(self, repo_url: str) -> str:
        import subprocess
        import re

        nom_repo = re.sub(r"\.git$", "", repo_url.rstrip("/").split("/")[-1])
        chemin_destination = f"{self._chemin_projet_complet}/external/{nom_repo}"

        try:
            resultat = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, chemin_destination],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
        except subprocess.TimeoutExpired:
            return f"Le clonage de {repo_url} a pris trop de temps (timeout)."

        if resultat.returncode != 0:
            return f"Échec du clonage de {repo_url} : {resultat.stderr[:300]}"

        self._code_search = PythonCodeSearchService(self._chemin_projet_complet)
        return (
            f"Dépôt '{nom_repo}' importé avec succès dans external/{nom_repo}. "
            f"Utilise get_project_structure pour voir son contenu réel avant toute proposition."
        )

    def test_function(self, file_path: str, function_name: str, arguments: dict) -> str:
        chemin_absolu = build_project_file_path(
            self._c.settings.generated_projects_dir, self._project_name, file_path
        )
        if not self._c.file_system.file_exists(chemin_absolu):
            return f"Fichier '{file_path}' introuvable."

        if file_path.endswith(".py"):
            return self._test_function_python(chemin_absolu, function_name, arguments)
        if file_path.endswith(".php"):
            return self._test_function_php(chemin_absolu, function_name, arguments)
        if file_path.endswith(".js"):
            return self._test_function_js(chemin_absolu, function_name, arguments)
        return f"Langage de {file_path} non supporté pour l'exécution directe."

    def _test_function_python(self, chemin_absolu: str, function_name: str, arguments: dict) -> str:
        import importlib.util
        try:
            spec = importlib.util.spec_from_file_location("module_teste", chemin_absolu)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            return f"Erreur lors du chargement du fichier : {e}"
        fonction = getattr(module, function_name, None)
        if fonction is None:
            return f"Fonction '{function_name}' introuvable."
        try:
            resultat = fonction(**arguments)
            return f"Résultat de {function_name}({arguments}) : {resultat!r}"
        except Exception as e:
            return f"Erreur lors de l'exécution : {e}"

    def _test_function_php(self, chemin_absolu: str, function_name: str, arguments: dict) -> str:
        import subprocess, json
        args_php = ", ".join(json.dumps(v) for v in arguments.values())
        script = f"require '{chemin_absolu}'; echo json_encode({function_name}({args_php}));"
        try:
            resultat = subprocess.run(["php", "-r", script], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        except FileNotFoundError:
            return "PHP n'est pas installé/accessible sur cette machine."
        except subprocess.TimeoutExpired:
            return "Timeout lors de l'exécution PHP."
        if resultat.returncode != 0:
            return f"Erreur PHP : {resultat.stderr[:300]}"
        return f"Résultat de {function_name}({arguments}) : {resultat.stdout.strip()}"

    def _test_function_js(self, chemin_absolu: str, function_name: str, arguments: dict) -> str:
        import subprocess, json
        args_js = ", ".join(json.dumps(v) for v in arguments.values())
        script = f"const m = require('{chemin_absolu}'); console.log(JSON.stringify(m.{function_name}({args_js})));"
        try:
            resultat = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        except FileNotFoundError:
            return "Node.js n'est pas installé/accessible sur cette machine."
        except subprocess.TimeoutExpired:
            return "Timeout lors de l'exécution JS."
        if resultat.returncode != 0:
            return f"Erreur JS : {resultat.stderr[:300]}"
        return f"Résultat de {function_name}({arguments}) : {resultat.stdout.strip()}"

    def read_file(self, file_path: str) -> str:
        """Lit le contenu RÉEL d'un fichier du Workspace actif, sans le modifier."""
        from pathlib import Path
        # Sprint 26 : pointer vers le repo du Workspace actif, pas generated_projects
        file_path_norm = file_path.replace("\\", "/")
        chemin_absolu = Path(self._chemin_projet_complet) / file_path_norm
        if not chemin_absolu.exists():
            return f"Fichier '{file_path}' introuvable dans le Workspace actif."
        try:
            contenu = chemin_absolu.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            return f"Erreur lecture : {e}"
        if len(contenu) > 4000:
            return contenu[:4000] + "\n... (fichier tronqué)"
        return contenu

    def run_tests(self) -> str:
        """Exécute réellement la suite de tests du projet (pytest, PHPUnit)."""
        import subprocess
        from pathlib import Path
        racine = self._chemin_projet_complet
        resultats = []

        if list(Path(racine).rglob("test_*.py")):
            r = subprocess.run(
                ["python", "-m", "pytest", racine, "-v"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            resultats.append(f"--- pytest ---\n{r.stdout[-1000:]}\n{r.stderr[-500:]}")

        chemin_phpunit = f"{racine}/vendor/bin/phpunit"
        if self._c.file_system.file_exists(chemin_phpunit):
            r = subprocess.run(
                [chemin_phpunit], cwd=racine,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            resultats.append(f"--- PHPUnit ---\n{r.stdout[-1000:]}\n{r.stderr[-500:]}")

        if not resultats:
            return "Aucun test détecté automatiquement."
        return "\n\n".join(resultats)

    def query_database(self, query: str) -> str:
        try:
            resultats = self._get_database().execute_query(query)
            return str(resultats) if resultats else "Aucun résultat."
        except Exception as e:
            return f"Erreur : {e}"

    def get_database_schema(self) -> str:
        return self._get_database().get_schema()

    def index_project(self) -> str:
        from config import credentials_store
        if not credentials_store.get("GEMINI_API_KEY"):
            return "La Knowledge Base nécessite GEMINI_API_KEY."
        return self._get_incremental_indexing_service().reindex_incremental(self._chemin_projet_complet)

    def search_knowledge_base(self, query: str) -> str:
        from config import credentials_store
        if not credentials_store.get("GEMINI_API_KEY"):
            return "La Knowledge Base nécessite GEMINI_API_KEY."
        return self._get_knowledge_base_service().search(query)

    def list_resources(self) -> str:
        disponibles = self._c.resource_service.list_project_resources(self._project_name)
        partagees = self._lister_resources_partagees()
        toutes = [f"{r} (projet)" for r in disponibles] + [f"{r} (partagée)" for r in partagees]
        return ", ".join(toutes) if toutes else "Aucune resource trouvée."

    def _lister_resources_partagees(self) -> list:
        from pathlib import Path
        dossier_partage = Path(self._c.settings.generated_projects_dir) / "_shared" / "resources"
        if not dossier_partage.exists():
            return []
        return [f.name for f in dossier_partage.glob("*.md")]

    def read_resource(self, resource_name: str) -> str:
        """Lit une Resource du Workspace actif."""
        # Sprint 26 : chercher d'abord dans le dossier resources du Workspace actif
        if self._active_workspace_id is not None:
            from pathlib import Path
            resources_path = Path(self._workspace_service.get_resources_path(self._active_workspace_id))
            chemin = resources_path / resource_name
            if chemin.exists():
                return chemin.read_text(encoding="utf-8", errors="ignore")
        try:
            resource = self._c.resource_service.load_resource(self._project_name, resource_name)
            return resource.content
        except Exception:
            contenu_partage = self._lire_resource_partagee(resource_name)
            if contenu_partage is not None:
                return contenu_partage
            return f"Erreur : Resource '{resource_name}' introuvable."

    def _lire_resource_partagee(self, resource_name: str) -> "str | None":
        from pathlib import Path
        chemin = Path(self._c.settings.generated_projects_dir) / "_shared" / "resources" / resource_name
        if chemin.exists():
            return chemin.read_text(encoding="utf-8")
        return None

    def list_available_generators(self) -> str:
        return ", ".join(self._c.prompt_service.list_available_prompts())

    def get_project_structure(self) -> str:
        """Renvoie l'arborescence réelle des fichiers du Workspace actif."""
        from pathlib import Path
        if self._active_workspace_id is not None:
            racine = Path(self._chemin_projet_complet)
            if racine.exists():
                lignes = []
                for f in sorted(racine.rglob("*")):
                    if any(p in {".git", "vendor", "node_modules", "__pycache__"} for p in f.parts):
                        continue
                    rel = str(f.relative_to(racine)).replace("\\", "/")
                    lignes.append(rel)
                return "\n".join(lignes[:500]) if lignes else "Dossier vide."
        return self._code_search.get_project_structure()

    def check_existing_feature(self, feature_name_hint: str) -> str:
        exactes = self._code_search.find_function(feature_name_hint)
        if exactes:
            return f"EXISTE DÉJÀ (nom exact) : {exactes[0].describe()}. Docstring : {exactes[0].docstring}"
        proches = self._code_search.find_similar_function_names(feature_name_hint)
        if proches:
            descriptions = "; ".join(p.describe() for p in proches)
            return f"Fonctionnalité(s) proche(s) trouvée(s) : {descriptions}"
        return "Aucune fonctionnalité existante trouvée pour ce nom."

    def find_project_file(self, file_name_hint: str) -> str:
        """Cherche un fichier du Workspace actif par son nom."""
        from pathlib import Path
        chemin_racine = Path(self._chemin_projet_complet)
        if not chemin_racine.exists():
            return "Workspace actif introuvable."
        indice = file_name_hint.lower()
        trouves = [
            str(f.relative_to(chemin_racine)).replace("\\", "/")
            for f in chemin_racine.rglob("*")
            if f.is_file() and indice in f.name.lower()
        ]
        if not trouves:
            return f"Aucun fichier correspondant à '{file_name_hint}' trouvé."
        return "Fichiers trouvés : " + ", ".join(trouves[:20])

    def _calculer_modification_fonction(self, function_name: str) -> "dict | None":
        localisation = self._code_search.get_function_source(function_name)
        if localisation is None:
            return None
        fichier_relatif, ligne_debut, ligne_fin, code_actuel = localisation
        return {"file_path": fichier_relatif, "line_start": ligne_debut, "line_end": ligne_fin, "original_code": code_actuel}

    def _generer_nouveau_contenu_fonction(self, code_actuel: str, modification_instruction: str) -> str:
        try:
            regles = self._c.resource_service.load_resource(self._project_name, "business_rules.md").content
        except Exception:
            regles = ""
        prompt = (
            f"Voici une fonction Python existante :\n\n```python\n{code_actuel}\n```\n\n"
            f"Modifie-la ainsi : {modification_instruction}\n\nRègles métier :\n{regles}\n\n"
            "IMPORTANT : renvoie UNIQUEMENT le code de la fonction modifiée, en Markdown python."
        )
        return extract_code_block(self._c.generation_service._llm_provider.generate(prompt))

    def _resoudre_chemin_reel(self, chemin_ou_nom: str) -> "str | None":
        from pathlib import Path
        # Sprint 26 : chercher dans le repo du Workspace actif
        racine = Path(self._chemin_projet_complet)
        chemin_direct = racine / chemin_ou_nom.replace("\\", "/")
        if chemin_direct.exists():
            return chemin_ou_nom.replace("\\", "/")

        nom_fichier = Path(chemin_ou_nom).name
        correspondances = list(racine.rglob(nom_fichier))
        if len(correspondances) == 1:
            return str(correspondances[0].relative_to(racine)).replace("\\", "/")
        return None

    def _generer_nouveau_contenu_fichier(self, file_path: str, modification_instruction: str) -> "dict | None":
        chemin_resolu = self._resoudre_chemin_reel(file_path)
        if chemin_resolu is None:
            return None
        file_path = chemin_resolu

        from pathlib import Path
        chemin_absolu = Path(self._chemin_projet_complet) / file_path
        try:
            contenu_original = chemin_absolu.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        extension_vers_langage = {
            ".php": "PHP", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
            ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".html": "HTML", ".css": "CSS",
            ".py": "Python", ".twig": "Twig",
        }
        extension = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        langage = extension_vers_langage.get(extension, "le même langage que l'original")

        try:
            guidelines = self._c.resource_service.load_resource(self._project_name, "coding_guidelines.md").content
        except Exception:
            guidelines = ""

        prompt = (
            f"Voici un fichier {langage} existant ({file_path}) :\n\n```\n{contenu_original}\n```\n\n"
            f"Modifie-le ainsi : {modification_instruction}\n\nConventions :\n{guidelines}\n\n"
            f"RÈGLES STRICTES :\n"
            f"1. Modifie UNIQUEMENT ce qui est demandé — rien d'autre.\n"
            f"2. Ne reformate PAS le code, ne change PAS les classes CSS non mentionnées.\n"
            f"3. Ne réorganise PAS la structure HTML.\n"
            f"4. Renvoie le fichier COMPLET en {langage}, un seul bloc Markdown.\n"
            f"5. Si tu changes une classe CSS, change UNIQUEMENT cette classe, rien autour."
        )
        nouveau_contenu = extract_code_block(self._c.generation_service._llm_provider.generate(prompt))
        return {
            "file_path": file_path,
            "new_content": nouveau_contenu,
            "old_content": contenu_original,
        }

    def _generer_nouveau_fichier(self, file_path: str, description: str) -> str:
        extension_vers_langage = {
            ".php": "PHP", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
            ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".py": "Python", ".twig": "Twig",
        }
        extension = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        langage = extension_vers_langage.get(extension, "le langage approprié")
        try:
            regles = self._c.resource_service.load_resource(self._project_name, "business_rules.md").content
        except Exception:
            regles = ""
        prompt = (
            f"Crée un nouveau fichier {langage} à l'emplacement {file_path}.\n\n"
            f"Ce que ce fichier doit faire : {description}\n\nRègles métier :\n{regles}\n\n"
            f"Renvoie UNIQUEMENT le code dans un seul bloc Markdown."
        )
        return extract_code_block(self._c.generation_service._llm_provider.generate(prompt))

    def _calculer_hash_projet(self, chemins_fichiers: list) -> dict:
        import hashlib
        from pathlib import Path
        empreintes = {}
        for chemin_relatif in chemins_fichiers:
            chemin_absolu = Path(self._chemin_projet_complet) / chemin_relatif.replace("\\", "/")
            if chemin_absolu.exists():
                contenu = chemin_absolu.read_text(encoding="utf-8", errors="ignore")
                empreintes[chemin_relatif] = hashlib.sha256(contenu.encode("utf-8")).hexdigest()
            else:
                empreintes[chemin_relatif] = "ABSENT"
        return empreintes

    def create_plan(self, user_request: str, resources_consulted: list, duplication_check: str, steps: list) -> str:
        import uuid as _uuid
        from datetime import datetime, timezone
        from core.entities.execution_plan import ExecutionPlan, PlanStep
        from pathlib import Path

        plan_id = str(_uuid.uuid4())[:8]
        etapes_construites = []
        chemins_a_verifier = []
        fichiers_concernes_par_ce_plan = []

        for i, etape_brute in enumerate(steps):
            action_type = etape_brute.get("action_type")
            target = etape_brute.get("target", "")
            description = etape_brute.get("description", "")
            instruction = etape_brute.get("instruction", "")

            if action_type == "modify_function":
                info = self._calculer_modification_fonction(target)
                if info is None:
                    return f"Impossible de créer le plan : fonction '{target}' introuvable."
                nouveau_code = self._generer_nouveau_contenu_fonction(info["original_code"], instruction)
                etapes_construites.append(PlanStep(
                    step_id=f"{plan_id}-{i}", action_type=action_type, target=target, description=description,
                    arguments={**info, "new_code": nouveau_code},
                ))
                chemins_a_verifier.append(info["file_path"])
                fichiers_concernes_par_ce_plan.append(info["file_path"])

            elif action_type == "modify_file":
                info = self._generer_nouveau_contenu_fichier(target, instruction)
                if info is None:
                    return f"Impossible de créer le plan : fichier '{target}' introuvable."
                etapes_construites.append(PlanStep(
                    step_id=f"{plan_id}-{i}", action_type=action_type, target=target, description=description,
                    arguments={**info, "modification_instruction": instruction},  # ← ajoute ca
                ))
                chemins_a_verifier.append(target)
                fichiers_concernes_par_ce_plan.append(target)

            elif action_type == "create_file":
                contenu = self._generer_nouveau_fichier(target, instruction)
                etapes_construites.append(PlanStep(
                    step_id=f"{plan_id}-{i}", action_type=action_type, target=target, description=description,
                    arguments={"content": contenu},
                ))
                chemins_a_verifier.append(target)
                fichiers_concernes_par_ce_plan.append(target)

            elif action_type == "git_push":
                arguments_etape = dict(etape_brute.get("arguments", {}))
                arguments_etape["files_to_add"] = list(fichiers_concernes_par_ce_plan)
                etapes_construites.append(PlanStep(
                    step_id=f"{plan_id}-{i}", action_type=action_type, target=target, description=description,
                    arguments=arguments_etape,
                ))

            elif action_type in ("database_write", "create_pull_request"):
                etapes_construites.append(PlanStep(
                    step_id=f"{plan_id}-{i}", action_type=action_type, target=target, description=description,
                    arguments=etape_brute.get("arguments", {}),
                ))

            else:
                return f"Type d'action inconnu dans le plan : '{action_type}'."

        plan = ExecutionPlan(
            plan_id=plan_id,
            project_name=self._project_name,
            user_request=user_request,
            resources_consulted=resources_consulted,
            duplication_check=duplication_check,
            steps=etapes_construites,
            project_state_hash=self._calculer_hash_projet(chemins_a_verifier),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._get_plan_storage().save(plan)
        self._get_audit_logger().record("plan_created", {
            "plan_id": plan_id, "user_request": user_request, "nb_steps": len(etapes_construites),
        })
        return (
            f"Plan créé (plan_id={plan_id}), {len(etapes_construites)} étape(s) prévue(s). "
            f"Présente ce plan clairement à l'utilisateur. Si l'utilisateur confirme dans le chat "
            f"(par exemple 'oui', 'approuve', 'vas-y'), appelle immédiatement le tool approve_plan "
            f"avec plan_id='{plan_id}' — c'est autorisé et attendu."
        )
