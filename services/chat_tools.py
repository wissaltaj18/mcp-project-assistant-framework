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

from services.code_search_service import PythonCodeSearchService
from tools.file_tools import build_project_file_path
from utils.string_utils import extract_code_block


class ChatTools:
    """Regroupe les actions qu'un agent conversationnel peut décider d'exécuter."""

    def __init__(self, container, project_name: str = "aegisai", repo_path: "str | None" = None):
        self._c = container
        self._project_name = project_name
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

    def _get_knowledge_base_service(self):
        if self._knowledge_base_service is None:
            from llm.gemini_embedding_provider import GeminiEmbeddingProvider
            from infra.simple_vector_store import SimpleJsonVectorStore
            from services.knowledge_base_service import KnowledgeBaseService
            import os

            embedding_provider = GeminiEmbeddingProvider(api_key=os.getenv("GEMINI_API_KEY", ""))
            vector_store = SimpleJsonVectorStore(f"{self._chemin_projet_complet}/.knowledge_base.json")
            self._knowledge_base_service = KnowledgeBaseService(embedding_provider, vector_store)
        return self._knowledge_base_service

    def _get_incremental_indexing_service(self):
        if self._incremental_indexing_service is None:
            from llm.gemini_embedding_provider import GeminiEmbeddingProvider
            from infra.simple_vector_store import SimpleJsonVectorStore
            from infra.local_git_provider import LocalGitProvider
            from services.codebase_indexer_service import CodebaseIndexerService
            from services.incremental_indexing_service import IncrementalIndexingService
            import os

            embedding_provider = GeminiEmbeddingProvider(api_key=os.getenv("GEMINI_API_KEY", ""))
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

    # ---------- Lecture / analyse (toujours accessibles au LLM) ----------

    def import_external_repository(self, repo_url: str) -> str:
        """
        Clone un dépôt Git externe (GitHub, GitLab...) dans le projet
        actif, sous "external/". N'écrit dans AUCUN fichier existant.

        Args:
            repo_url: URL du dépôt à cloner
        """
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
        """
        Exécute RÉELLEMENT une fonction avec des paramètres donnés.
        Fonctionne pour Python, PHP et JS autonomes (sans dépendances
        injectées complexes -- les méthodes de service Symfony/Spring
        avec injection ne peuvent pas être testées isolément).

        Args:
            file_path: Chemin relatif du fichier contenant la fonction
            function_name: Nom exact de la fonction à tester
            arguments: Arguments à passer à la fonction
        """
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
            return (
                "PHP n'est pas installé/accessible sur cette machine. Note : les "
                "méthodes de classes Symfony avec dépendances injectées ne peuvent "
                "de toute façon pas être testées isolément sans faire tourner toute l'application."
            )
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
        """
        Lit le contenu RÉEL d'un fichier, sans le modifier.

        Args:
            file_path: Chemin relatif exact du fichier
        """
        chemin_absolu = build_project_file_path(
            self._c.settings.generated_projects_dir, self._project_name, file_path
        )
        if not self._c.file_system.file_exists(chemin_absolu):
            return f"Fichier '{file_path}' introuvable."
        contenu = self._c.file_system.read_file(chemin_absolu)
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
            return (
                "Aucun test détecté automatiquement (ni pytest, ni PHPUnit via "
                "vendor/bin/phpunit -- pour PHP, lance 'composer install' d'abord)."
            )
        return "\n\n".join(resultats)

    def query_database(self, query: str) -> str:
        """
        Exécute une requête de LECTURE (SELECT) sur la base de données du projet.

        Args:
            query: Requête SQL SELECT uniquement
        """
        try:
            resultats = self._get_database().execute_query(query)
            return str(resultats) if resultats else "Aucun résultat."
        except Exception as e:
            return f"Erreur : {e}"

    def get_database_schema(self) -> str:
        """Renvoie les tables et colonnes réellement présentes dans la base de données du projet."""
        return self._get_database().get_schema()

    def index_project(self) -> str:
        """Indexe le code du projet dans la Knowledge Base (RAG). NÉCESSITE GEMINI_API_KEY."""
        import os
        if not os.getenv("GEMINI_API_KEY"):
            return "La Knowledge Base nécessite GEMINI_API_KEY. Utilise plutôt check_existing_feature ou find_project_file."
        return self._get_incremental_indexing_service().reindex_incremental(self._chemin_projet_complet)

    def search_knowledge_base(self, query: str) -> str:
        """
        Recherche sémantique dans le code du projet. NÉCESSITE GEMINI_API_KEY.

        Args:
            query: La question en langage naturel
        """
        import os
        if not os.getenv("GEMINI_API_KEY"):
            return "La Knowledge Base nécessite GEMINI_API_KEY. Utilise plutôt check_existing_feature."
        return self._get_knowledge_base_service().search(query)

    def list_resources(self) -> str:
        """
        Liste les fichiers de règles et de contexte (Resources) disponibles
        -- celles propres au projet actif, PLUS celles partagées entre
        tous les projets (dossier _shared).
        """
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
        """
        Lit le contenu d'une Resource -- cherche d'abord dans le projet
        actif, puis dans les Resources partagées entre projets (_shared).

        Args:
            resource_name: Nom exact du fichier, ex: business_rules.md
        """
        try:
            resource = self._c.resource_service.load_resource(self._project_name, resource_name)
            return resource.content
        except Exception:
            contenu_partage = self._lire_resource_partagee(resource_name)
            if contenu_partage is not None:
                return contenu_partage
            return f"Erreur : Resource '{resource_name}' introuvable, ni dans le projet ni dans les Resources partagées."

    def _lire_resource_partagee(self, resource_name: str) -> "str | None":
        from pathlib import Path
        chemin = Path(self._c.settings.generated_projects_dir) / "_shared" / "resources" / resource_name
        if chemin.exists():
            return chemin.read_text(encoding="utf-8")
        return None

    def list_available_generators(self) -> str:
        """Liste les générateurs de pages internes historiques (informationnel)."""
        return ", ".join(self._c.prompt_service.list_available_prompts())

    def get_project_structure(self) -> str:
        """Renvoie l'arborescence réelle des fichiers de code du projet actif, tous langages confondus."""
        return self._code_search.get_project_structure()

    def check_existing_feature(self, feature_name_hint: str) -> str:
        """
        Vérifie si une fonctionnalité liée existe DÉJÀ, avant d'en proposer une nouvelle.

        Args:
            feature_name_hint: Un nom probable de fonction
        """
        exactes = self._code_search.find_function(feature_name_hint)
        if exactes:
            return f"EXISTE DÉJÀ (nom exact) : {exactes[0].describe()}. Docstring : {exactes[0].docstring}"
        proches = self._code_search.find_similar_function_names(feature_name_hint)
        if proches:
            descriptions = "; ".join(p.describe() for p in proches)
            return f"Fonctionnalité(s) proche(s) trouvée(s) : {descriptions}"
        return "Aucune fonctionnalité existante trouvée pour ce nom."

    def find_project_file(self, file_name_hint: str) -> str:
        """
        Cherche un fichier du projet par son nom, quel que soit son type.

        Args:
            file_name_hint: Nom exact ou partiel du fichier
        """
        from pathlib import Path
        racine = f"{self._c.settings.generated_projects_dir}/{self._project_name}"
        chemin_racine = Path(racine)
        if not chemin_racine.exists():
            return "Projet introuvable."
        indice = file_name_hint.lower().replace(".html", "").replace(".css", "").replace(".js", "")
        trouves = [
            str(f.relative_to(chemin_racine))
            for f in chemin_racine.rglob("*")
            if f.is_file() and indice in f.name.lower()
        ]
        if not trouves:
            return f"Aucun fichier correspondant à '{file_name_hint}' trouvé."
        return "Fichiers trouvés : " + ", ".join(trouves)

    # ---------- Calculs internes pour create_plan (jamais appelés directement par le LLM) ----------

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
        return extract_code_block(self._c.llm_provider.generate(prompt))

    def _resoudre_chemin_reel(self, chemin_ou_nom: str) -> "str | None":
        """
        Si le chemin donné existe tel quel, le renvoie directement. Sinon,
        cherche un fichier du même NOM n'importe où dans le projet -- rend
        le système tolérant si le LLM donne juste 'Cart.php' au lieu du
        chemin complet 'external/E-commerce/src/Entity/Cart.php'.
        """
        chemin_absolu = build_project_file_path(
            self._c.settings.generated_projects_dir, self._project_name, chemin_ou_nom
        )
        if self._c.file_system.file_exists(chemin_absolu):
            return chemin_ou_nom

        from pathlib import Path
        racine = Path(f"{self._c.settings.generated_projects_dir}/{self._project_name}")
        nom_fichier = Path(chemin_ou_nom).name
        correspondances = list(racine.rglob(nom_fichier))
        if len(correspondances) == 1:
            return str(correspondances[0].relative_to(racine))
        return None

    def _generer_nouveau_contenu_fichier(self, file_path: str, modification_instruction: str) -> "dict | None":
        chemin_resolu = self._resoudre_chemin_reel(file_path)
        if chemin_resolu is None:
            return None
        file_path = chemin_resolu

        chemin_absolu = build_project_file_path(self._c.settings.generated_projects_dir, self._project_name, file_path)
        contenu_original = self._c.file_system.read_file(chemin_absolu)

        extension_vers_langage = {
            ".php": "PHP", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
            ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".html": "HTML", ".css": "CSS", ".py": "Python",
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
            f"IMPORTANT : le fichier reste en {langage}. Renvoie le fichier COMPLET modifié, un seul bloc Markdown."
        )
        nouveau_contenu = extract_code_block(self._c.llm_provider.generate(prompt))
        return {"file_path": file_path, "original_content": contenu_original, "new_content": nouveau_contenu, "language": langage}

    def _generer_nouveau_fichier(self, file_path: str, description: str) -> str:
        extension_vers_langage = {
            ".php": "PHP", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
            ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".py": "Python",
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
        return extract_code_block(self._c.llm_provider.generate(prompt))

    def _calculer_hash_projet(self, chemins_fichiers: list) -> dict:
        """Empreinte SHA-256 de chaque fichier référencé -- détecte un changement entre création et exécution du plan."""
        import hashlib
        empreintes = {}
        for chemin_relatif in chemins_fichiers:
            chemin_absolu = build_project_file_path(self._c.settings.generated_projects_dir, self._project_name, chemin_relatif)
            if self._c.file_system.file_exists(chemin_absolu):
                contenu = self._c.file_system.read_file(chemin_absolu)
                empreintes[chemin_relatif] = hashlib.sha256(contenu.encode("utf-8")).hexdigest()
            else:
                empreintes[chemin_relatif] = "ABSENT"
        return empreintes

    # ---------- La SEULE capacité d'écriture du LLM : proposer un plan ----------

    def create_plan(self, user_request: str, resources_consulted: list, duplication_check: str, steps: list) -> str:
        """
        Crée un VRAI plan d'exécution, avec le contenu exact déjà calculé
        pour chaque étape -- ne l'exécute PAS. Seul un utilisateur, via un
        bouton dans l'interface (jamais toi), peut approuver et déclencher
        l'exécution réelle.

        IMPORTANT : lis TOUJOURS les vrais fichiers (get_project_structure,
        read_file, check_existing_feature) AVANT d'appeler create_plan.
        N'invente JAMAIS un fichier, un langage, ou un contenu qui ne
        correspond pas à ce que tu as réellement lu.

        Args:
            user_request: Résumé de la demande originale
            resources_consulted: Noms des Resources lues avant ce plan
            duplication_check: Résultat exact de check_existing_feature
            steps: Liste d'étapes, chacune avec "action_type"
                ("modify_function", "modify_file", "create_file",
                "database_write", "git_push", "create_pull_request"),
                "target", "description", "instruction" (fichiers), et
                "arguments" (pour database_write/git_push/create_pull_request)
        """
        import uuid as _uuid
        from datetime import datetime, timezone
        from core.entities.execution_plan import ExecutionPlan, PlanStep

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
                    return f"Impossible de créer le plan : fonction '{target}' introuvable. Vérifie le vrai nom avec check_existing_feature d'abord."
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
                    return f"Impossible de créer le plan : fichier '{target}' introuvable. Vérifie le vrai chemin avec find_project_file d'abord."
                etapes_construites.append(PlanStep(
                    step_id=f"{plan_id}-{i}", action_type=action_type, target=target, description=description,
                    arguments=info,
                ))
                chemins_a_verifier.append(target)
                fichiers_concernes_par_ce_plan.append(target)

            elif action_type == "create_file":
                extension_cible = "." + target.rsplit(".", 1)[-1] if "." in target else ""
                structure_reelle = self._code_search.get_project_structure()
                if extension_cible and extension_cible not in structure_reelle and structure_reelle.strip():
                    return (
                        f"Impossible de créer le plan : le fichier '{target}' est en "
                        f"'{extension_cible}', mais AUCUN fichier de ce type n'existe dans le "
                        f"projet réel (structure actuelle : {structure_reelle[:200]}...). "
                        f"Vérifie que tu lis bien le VRAI projet, pas un exemple générique."
                    )
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
            f"Plan créé (plan_id={plan_id}), en attente de confirmation de l'UTILISATEUR "
            f"dans l'interface -- toi, l'agent, tu ne peux PAS l'approuver. "
            f"{len(etapes_construites)} étape(s) prévue(s). "
            f"Présente ce plan clairement et attends que l'utilisateur l'approuve ou le rejette "
            f"via les boutons de l'interface."
        )