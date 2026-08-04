"""
Schemas des tools de l'agent conversationnel, en un seul endroit. Chaque
provider (Gemini, Ollama, Claude...) construit sa propre representation a
partir de cette liste -- une seule source de verite pour les 3 providers.

REGLE DE SECURITE STRUCTURELLE : le LLM n'a acces a AUCUN tool qui
modifie un fichier, ecrit en base de donnees, cree un commit, un push,
ou une pull request -- directement. Sa SEULE capacite d'ecriture est
create_plan, qui ne fait que PROPOSER (calcule et fige le contenu exact,
mais n'ecrit rien). Seul un clic utilisateur dans l'interface, via
l'endpoint HTTP /api/v1/plans/{id}/approve (jamais vu par le LLM),
declenche l'execution reelle via PlanExecutorService.
"""

TOOL_SCHEMAS = [
   {
        "name": "create_workspace",
        "description": "Crée un nouveau Workspace à partir d'un dépôt Git : clone le dépôt et prépare le terrain pour les futures analyses. Ne rend PAS ce Workspace actif automatiquement.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_url": {"type": "string", "description": "URL du dépôt Git, ex: https://github.com/user/repo.git"},
                "branch": {"type": "string", "description": "Branche spécifique à cloner (optionnel)"},
                "auth_token": {"type": "string", "description": "Token d'authentification pour un dépôt privé (optionnel)"},
            },
            "required": ["repo_url"],
        },
    },
    {
        "name": "set_preference",
        "description": "Définit une préférence de workflow pour un Workspace (ex: run_tests_before_push=false, architecture_style=DDD), respectée automatiquement ensuite.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Identifiant du Workspace concerné"},
                "key": {"type": "string", "description": "Nom de la préférence, ex: run_tests_before_push"},
                "value": {"type": "string", "description": "Valeur de la préférence, ex: false"},
            },
            "required": ["workspace_id", "key", "value"],
        },
    },
    {
        "name": "set_active_workspace",
        "description": "Active un Workspace deja cree -- toutes les operations suivantes (lecture, plans, RAG) porteront dessus.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Identifiant du Workspace, renvoye par create_workspace"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "generate_resources",
        "description": "Genere les Resources (architecture technique, et a terme fonctionnelle/regles) d'un Workspace, depuis son analyse d'architecture.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Identifiant du Workspace concerne"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "index_workspace",
        "description": "Indexe le code d'un Workspace dans sa base vectorielle (RAG). Necessite GEMINI_API_KEY configure.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Identifiant du Workspace concerne"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "prepare_workspace",
        "description": "Workflow complet en un seul appel : clone le depot, cree et active le Workspace, genere ses Resources, l'indexe dans le RAG. Une fois termine, tous les autres tools operent automatiquement sur ce Workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_url": {"type": "string", "description": "URL du depot Git a importer"},
                "branch": {"type": "string", "description": "Branche specifique a cloner (optionnel)"},
            },
            "required": ["repo_url"],
        },
    },
    {
        "name": "list_resources",
        "description": "Liste les fichiers de regles et de contexte (Resources) disponibles pour le projet actif.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "read_resource",
        "description": "Lit le contenu d'une Resource du projet (regles metier, conventions, architecture).",
        "parameters": {
            "type": "object",
            "properties": {"resource_name": {"type": "string", "description": "Nom exact du fichier, ex: business_rules.md"}},
            "required": ["resource_name"],
        },
    },
    {
        "name": "list_available_generators",
        "description": "Liste les generateurs de pages internes historiques disponibles (informationnel uniquement).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_project_structure",
        "description": "Renvoie l'arborescence reelle des fichiers de code du projet actif, tous langages confondus.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "check_existing_feature",
        "description": "Verifie si une fonctionnalite liee existe DEJA dans le code avant d'en proposer une nouvelle. A utiliser TOUJOURS avant create_plan.",
        "parameters": {
            "type": "object",
            "properties": {"feature_name_hint": {"type": "string", "description": "Un nom probable de fonction, ex: calculate_salary"}},
            "required": ["feature_name_hint"],
        },
    },
    {
        "name": "find_project_file",
        "description": "Cherche un fichier du projet par son nom, quel que soit son type (HTML, CSS, JS, PHP, Python...).",
        "parameters": {
            "type": "object",
            "properties": {"file_name_hint": {"type": "string", "description": "Nom exact ou partiel du fichier"}},
            "required": ["file_name_hint"],
        },
    },
    {
        "name": "read_file",
        "description": "Lit le contenu reel d'un fichier, sans le modifier.",
        "parameters": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "Chemin relatif exact du fichier"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "run_tests",
        "description": "Execute reellement la suite de tests du projet (pytest, PHPUnit) -- diagnostic, ne modifie rien.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "query_database",
        "description": "Execute une requete de LECTURE (SELECT) sur la base de donnees du projet.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Requete SQL SELECT uniquement"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_database_schema",
        "description": "Renvoie les tables et colonnes reellement presentes dans la base de donnees du projet.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "import_external_repository",
        "description": "Clone un depot Git externe (GitHub...) dans le projet actif, pour pouvoir l'analyser. N'ecrit dans AUCUN fichier existant du projet.",
        "parameters": {
            "type": "object",
            "properties": {"repo_url": {"type": "string", "description": "URL du depot, ex: https://github.com/user/repo.git"}},
            "required": ["repo_url"],
        },
    },
    {
        "name": "test_function",
        "description": "Execute une fonction existante avec des parametres donnes pour observer son comportement reel (diagnostic, ne modifie aucun fichier).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Chemin relatif du fichier contenant la fonction"},
                "function_name": {"type": "string", "description": "Nom exact de la fonction a tester"},
                "arguments": {"type": "object", "description": "Arguments a passer a la fonction"},
            },
            "required": ["file_path", "function_name", "arguments"],
        },
    },
    {
        "name": "index_project",
        "description": "Indexe (ou re-indexe de facon incrementale) le code du projet dans la Knowledge Base, pour la recherche semantique.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "search_knowledge_base",
        "description": "Recherche semantique dans le code du projet (par sens, pas juste par mots-cles).",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "La question en langage naturel"}},
            "required": ["query"],
        },
    },
    {
        "name": "update_resource",
        "description": "Modifie une Resource existante d'un Workspace (ou en crée une nouvelle) -- pour changer une règle de dev, ajouter une nouvelle règle (DDD...), ou corriger l'analyse automatique.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Identifiant du Workspace concerné"},
                "resource_name": {"type": "string", "description": "Nom du fichier, ex: development_rules.md"},
                "new_content": {"type": "string", "description": "Nouveau contenu complet de la Resource"},
            },
            "required": ["workspace_id", "resource_name", "new_content"],
        },
    },
    {
        "name": "create_plan",
        "description": (
            "SEULE facon de proposer une modification, une ecriture en base, un commit, un push, ou "
            "une pull request. Ne modifie RIEN, n'ecrit RIEN, ne pousse RIEN -- calcule et fige le "
            "contenu exact de chaque etape, puis attend l'approbation de l'UTILISATEUR dans "
            "l'interface. TOI, l'agent, tu ne peux JAMAIS approuver ce plan toi-meme -- seul un clic "
            "de l'utilisateur sur un bouton de l'interface declenche l'execution reelle. Appelle "
            "TOUJOURS check_existing_feature ET read_resource avant create_plan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {"type": "string", "description": "Resume de la demande originale de l'utilisateur"},
                "resources_consulted": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Noms des Resources lues avant de construire ce plan",
                },
                "duplication_check": {
                    "type": "string",
                    "description": "Resultat exact renvoye par check_existing_feature avant ce plan",
                },
                "steps": {
                    "type": "array",
                    "description": "Liste des etapes prevues",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ["modify_function", "modify_file", "create_file", "database_write", "git_push", "create_pull_request"],
                            },
                            "target": {"type": "string", "description": "Nom de fonction, chemin de fichier, ou nom de branche selon action_type"},
                            "description": {"type": "string", "description": "Explication lisible de cette etape"},
                            "instruction": {"type": "string", "description": "Ce qui doit changer/etre cree (fichiers uniquement)"},
                            "arguments": {"type": "object", "description": "Pour database_write (query, params) ou git_push/create_pull_request (commit_message, title, description)"},
                        },
                        "required": ["action_type", "target", "description"],
                    },
                },
            },
            "required": ["user_request", "resources_consulted", "duplication_check", "steps"],
        },
    },
]

SYSTEM_INSTRUCTION = (
    "Tu es l'assistant de developpement du framework, un veritable "
    "ingenieur logiciel assistant. Tu ne peux JAMAIS modifier un fichier, "
    "ecrire en base de donnees, committer, pousser sur Git, ou creer une "
    "pull request directement -- ta SEULE capacite d'ecriture est "
    "create_plan, qui ne fait que PROPOSER. L'utilisateur approuve ou "
    "rejette ensuite dans l'interface -- jamais toi.\n\n"
    "WORKFLOW OBLIGATOIRE, DANS CET ORDRE, POUR TOUTE DEMANDE DE "
    "MODIFICATION/CREATION :\n\n"
    "1. UNDERSTAND -- comprends la demande de l'utilisateur.\n\n"
    "2. ANALYZE -- utilise get_project_structure, find_project_file, "
    "read_file pour comprendre le code concerne.\n\n"
    "3. CONSULT RESOURCES -- utilise list_resources puis read_resource "
    "pour lire les regles metier et conventions pertinentes.\n\n"
    "4. CHECK DUPLICATION -- appelle TOUJOURS check_existing_feature "
    "avec le nom probable de la fonctionnalite, avant de proposer quoi "
    "que ce soit. Si une fonctionnalite similaire existe deja, propose "
    "de l'ETENDRE (action_type modify_function/modify_file), jamais de "
    "la dupliquer.\n\n"
    "5. CREATE PLAN -- appelle create_plan avec resources_consulted et "
    "duplication_check honnetement renseignes (les vrais resultats des "
    "etapes 3 et 4, jamais inventes), et les steps precis.\n\n"
    "6. Presente le plan clairement a l'utilisateur et attends son "
    "approbation ou son rejet dans l'INTERFACE -- ne demande jamais "
    "'oui/non' en conversation pour ca, le bouton de l'interface est le "
    "seul mecanisme valide.\n\n"
    "NE JAMAIS INVENTER : un fichier, une classe, une fonction, une "
    "route, une regle metier, une couleur, un comportement UX non "
    "demande. Si une information essentielle manque et changerait le "
    "resultat, pose une question de clarification au lieu de deviner. Si "
    "l'utilisateur ne precise pas un detail visuel (couleur, style), ne "
    "l'invente pas -- reste simple ou respecte les conventions deja "
    "presentes dans le code existant.\n\n"
    "Reponds TOUJOURS dans la meme langue que le dernier message de "
    "l'utilisateur. Sois clair, direct, et professionnel."
    
)