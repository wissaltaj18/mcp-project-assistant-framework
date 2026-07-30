"""
Schémas des tools de l'agent conversationnel, en un seul endroit. Chaque
provider (Gemini, Ollama, Claude...) construit sa propre représentation à
partir de cette liste -- une seule source de vérité pour les 3 providers.

RÈGLE DE SÉCURITÉ STRUCTURELLE : le LLM n'a accès à AUCUN tool qui
modifie un fichier, écrit en base de données, crée un commit, un push,
ou une pull request -- directement. Sa SEULE capacité d'écriture est
create_plan, qui ne fait que PROPOSER (calcule et fige le contenu exact,
mais n'écrit rien). Seul un clic utilisateur dans l'interface, via
l'endpoint HTTP /api/v1/plans/{id}/approve (jamais vu par le LLM),
déclenche l'exécution réelle via PlanExecutorService.
"""

TOOL_SCHEMAS = [
    {
        "name": "list_resources",
        "description": "Liste les fichiers de règles et de contexte (Resources) disponibles pour le projet actif.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "read_resource",
        "description": "Lit le contenu d'une Resource du projet (règles métier, conventions, architecture).",
        "parameters": {
            "type": "object",
            "properties": {"resource_name": {"type": "string", "description": "Nom exact du fichier, ex: business_rules.md"}},
            "required": ["resource_name"],
        },
    },
    {
        "name": "list_available_generators",
        "description": "Liste les générateurs de pages internes historiques disponibles (informationnel uniquement).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_project_structure",
        "description": "Renvoie l'arborescence réelle des fichiers de code du projet actif, tous langages confondus.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "check_existing_feature",
        "description": "Vérifie si une fonctionnalité liée existe DÉJÀ dans le code avant d'en proposer une nouvelle. À utiliser TOUJOURS avant create_plan.",
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
        "description": "Lit le contenu réel d'un fichier, sans le modifier.",
        "parameters": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "Chemin relatif exact du fichier"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "run_tests",
        "description": "Exécute réellement la suite de tests du projet (pytest, PHPUnit) -- diagnostic, ne modifie rien.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "query_database",
        "description": "Exécute une requête de LECTURE (SELECT) sur la base de données du projet.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Requête SQL SELECT uniquement"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_database_schema",
        "description": "Renvoie les tables et colonnes réellement présentes dans la base de données du projet.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "import_external_repository",
        "description": "Clone un dépôt Git externe (GitHub...) dans le projet actif, pour pouvoir l'analyser. N'écrit dans AUCUN fichier existant du projet.",
        "parameters": {
            "type": "object",
            "properties": {"repo_url": {"type": "string", "description": "URL du dépôt, ex: https://github.com/user/repo.git"}},
            "required": ["repo_url"],
        },
    },
    {
        "name": "test_function",
        "description": "Exécute une fonction existante avec des paramètres donnés pour observer son comportement réel (diagnostic, ne modifie aucun fichier).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Chemin relatif du fichier contenant la fonction"},
                "function_name": {"type": "string", "description": "Nom exact de la fonction à tester"},
                "arguments": {"type": "object", "description": "Arguments à passer à la fonction"},
            },
            "required": ["file_path", "function_name", "arguments"],
        },
    },
    {
        "name": "index_project",
        "description": "Indexe (ou ré-indexe de façon incrémentale) le code du projet dans la Knowledge Base, pour la recherche sémantique.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "search_knowledge_base",
        "description": "Recherche sémantique dans le code du projet (par sens, pas juste par mots-clés).",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "La question en langage naturel"}},
            "required": ["query"],
        },
    },
    {
        "name": "create_plan",
        "description": (
            "SEULE façon de proposer une modification, une écriture en base, un commit, un push, ou "
            "une pull request. Ne modifie RIEN, n'écrit RIEN, ne pousse RIEN -- calcule et fige le "
            "contenu exact de chaque étape, puis attend l'approbation de l'UTILISATEUR dans "
            "l'interface. TOI, l'agent, tu ne peux JAMAIS approuver ce plan toi-même -- seul un clic "
            "de l'utilisateur sur un bouton de l'interface déclenche l'exécution réelle. Appelle "
            "TOUJOURS check_existing_feature ET read_resource avant create_plan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {"type": "string", "description": "Résumé de la demande originale de l'utilisateur"},
                "resources_consulted": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Noms des Resources lues avant de construire ce plan",
                },
                "duplication_check": {
                    "type": "string",
                    "description": "Résultat exact renvoyé par check_existing_feature avant ce plan",
                },
                "steps": {
                    "type": "array",
                    "description": "Liste des étapes prévues",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ["modify_function", "modify_file", "create_file", "database_write", "git_push", "create_pull_request"],
                            },
                            "target": {"type": "string", "description": "Nom de fonction, chemin de fichier, ou nom de branche selon action_type"},
                            "description": {"type": "string", "description": "Explication lisible de cette étape"},
                            "instruction": {"type": "string", "description": "Ce qui doit changer/être créé (fichiers uniquement)"},
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
    "Tu es l'assistant de développement du framework, un véritable "
    "ingénieur logiciel assistant. Tu ne peux JAMAIS modifier un fichier, "
    "écrire en base de données, committer, pousser sur Git, ou créer une "
    "pull request directement -- ta SEULE capacité d'écriture est "
    "create_plan, qui ne fait que PROPOSER. L'utilisateur approuve ou "
    "rejette ensuite dans l'interface -- jamais toi.\n\n"
    "WORKFLOW OBLIGATOIRE, DANS CET ORDRE, POUR TOUTE DEMANDE DE "
    "MODIFICATION/CRÉATION :\n\n"
    "1. UNDERSTAND -- comprends la demande de l'utilisateur.\n\n"
    "2. ANALYZE -- utilise get_project_structure, find_project_file, "
    "read_file pour comprendre le code concerné.\n\n"
    "3. CONSULT RESOURCES -- utilise list_resources puis read_resource "
    "pour lire les règles métier et conventions pertinentes.\n\n"
    "4. CHECK DUPLICATION -- appelle TOUJOURS check_existing_feature "
    "avec le nom probable de la fonctionnalité, avant de proposer quoi "
    "que ce soit. Si une fonctionnalité similaire existe déjà, propose "
    "de l'ÉTENDRE (action_type modify_function/modify_file), jamais de "
    "la dupliquer.\n\n"
    "5. CREATE PLAN -- appelle create_plan avec resources_consulted et "
    "duplication_check honnêtement renseignés (les vrais résultats des "
    "étapes 3 et 4, jamais inventés), et les steps précis.\n\n"
    "6. Présente le plan clairement à l'utilisateur et attends son "
    "approbation ou son rejet dans l'INTERFACE -- ne demande jamais "
    "'oui/non' en conversation pour ça, le bouton de l'interface est le "
    "seul mécanisme valide.\n\n"
    "NE JAMAIS INVENTER : un fichier, une classe, une fonction, une "
    "route, une règle métier, une couleur, un comportement UX non "
    "demandé. Si une information essentielle manque et changerait le "
    "résultat, pose une question de clarification au lieu de deviner. Si "
    "l'utilisateur ne précise pas un détail visuel (couleur, style), ne "
    "l'invente pas -- reste simple ou respecte les conventions déjà "
    "présentes dans le code existant.\n\n"
    "Réponds TOUJOURS dans la même langue que le dernier message de "
    "l'utilisateur. Sois clair, direct, et professionnel."
)