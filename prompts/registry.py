"""
Registre central des PromptTemplate disponibles. Pour l'instant, les
templates sont définis ici en dur ; ils seront déplacés vers des fichiers
dédiés (generate_backend_prompt.py, etc.) au fur et à mesure du Lot 4.
"""

from core.entities.prompt_template import PromptTemplate

# Consigne pour les pages frontend (HTML autonome)
_CONSIGNE_RENDU_DEMO = (
    "RÈGLE ABSOLUE DE FORMAT, PLUS IMPORTANTE QUE LA STACK TECHNIQUE DU PROJET : "
    "génère UNIQUEMENT un fichier HTML autonome (HTML + CSS + JavaScript "
    "vanilla, tout dans un seul fichier). "
    "INTERDICTIONS STRICTES : aucun 'import', aucun 'export', aucune syntaxe "
    "JSX ou TypeScript, aucune librairie externe (pas de React, pas de "
    "lucide-react, pas d'antd, pas de framework JS d'aucune sorte). "
    "Pour les icônes, utilise des émojis Unicode ou du SVG écrit directement "
    "en dur dans le HTML, jamais une librairie d'icônes. "
    "Le fichier doit s'ouvrir et fonctionner en double-cliquant dessus dans "
    "un navigateur, sans aucune étape de compilation ou d'installation. "
    "Même si le contexte du projet mentionne React, ignore ce détail pour "
    "cette génération : seul le rendu HTML autonome compte ici."
)

# Consigne pour le backend (vraie logique Python exécutable, pas de simulation)

_CONSIGNE_BACKEND = (
    "Génère un unique fichier Python autonome utilisant FastAPI, structuré "
    "comme un ROUTER (pas une application complète) : utilise "
    "'router = APIRouter()' au lieu de créer 'app = FastAPI()'. Ce router "
    "sera importé et assemblé avec d'autres dans un fichier main.py central "
    "-- ne crée donc PAS d'instance FastAPI(), PAS de middleware CORS ici "
    "(géré ailleurs), juste le router et ses routes.\n\n"
    "Implémente une VRAIE route (endpoint) avec une logique métier réelle "
    "et exécutable -- pas un exemple simulé, pas de pseudo-code, pas de "
    "commentaire '# TODO' à la place de la logique. La route doit "
    "concrètement vérifier les règles ci-dessous (ex: comparer un montant "
    "à un seuil, lever une erreur HTTP 403 ou 429 appropriée si une règle "
    "est violée). Inclue tous les imports nécessaires (fastapi, pydantic "
    "si besoin).\n\n"
    "FORMAT DE RÉPONSE OBLIGATOIRE : mets tout le code Python dans un seul "
    "bloc de code Markdown avec le tag python. Ne mets JAMAIS la commande "
    "de lancement dans un bloc de code séparé."
)
# Consigne pour un backend d'authentification (rôles définis dans project_context.md)
_CONSIGNE_AUTH_BACKEND = (
    "Génère un unique fichier Python autonome utilisant FastAPI, structuré "
    "comme un ROUTER (pas une application complète) : utilise "
    "'router = APIRouter()' au lieu de créer 'app = FastAPI()'. Ce router "
    "sera importé et assemblé avec d'autres dans un fichier main.py central "
    "-- ne crée donc PAS d'instance FastAPI(), PAS de middleware CORS ici.\n\n"
    "Implémente un VRAI endpoint d'authentification POST /api/v1/auth/login. "
    "Utilise un dictionnaire Python en mémoire comme base d'utilisateurs de "
    "démonstration, avec au moins 3 comptes correspondant aux rôles décrits "
    "dans le contexte du projet ci-dessous (ex: admin, team_lead, developer), "
    "chacun avec un nom d'utilisateur, un mot de passe simple, et son rôle. "
    "La route doit VRAIMENT vérifier les identifiants reçus : renvoyer 200 "
    "avec le rôle de l'utilisateur si les identifiants sont corrects, "
    "renvoyer une erreur HTTP 401 avec un message clair si le mot de passe "
    "ou le nom d'utilisateur est incorrect. Ajoute aussi un compteur simple "
    "de tentatives échouées par utilisateur : après 3 échecs consécutifs, "
    "renvoie une erreur HTTP 429 (trop de tentatives) au lieu de 401. "
    "Ceci est un mot de passe en clair à but de démonstration uniquement -- "
    "ajoute un commentaire précisant qu'un vrai système utiliserait un "
    "hachage (bcrypt) et une vraie base de données.\n\n"
    "FORMAT DE RÉPONSE OBLIGATOIRE : mets tout le code Python dans un seul "
    "bloc de code Markdown avec le tag python. Ne mets JAMAIS la commande "
    "de lancement dans un bloc de code séparé."
)


def build_prompt_registry() -> dict[str, PromptTemplate]:
    return {
    "generate_login": PromptTemplate(
            name="generate_login",
            description="Génère la page de connexion, connectée au vrai backend d'authentification",
            template_text=(
                'Génère le code de la page de connexion "{page_name}".\n\n'
                "Ce formulaire doit envoyer une VRAIE requête POST à "
                "http://localhost:8000/api/v1/auth/login avec le corps JSON "
                "{{\"username\": \"...\", \"password\": \"...\"}}. "
                "N'invente AUCUNE vérification en JavaScript local -- laisse "
                "le serveur décider. Si la réponse est 200 : stocke le rôle et "
                "le token reçus dans sessionStorage, affiche un message de "
                "succès avec le rôle renvoyé par l'API, PUIS redirige "
                "automatiquement vers 'dashboard.html' après un court délai "
                "(environ 1 seconde, via setTimeout) pour laisser le temps de "
                "lire le message. Si la réponse est 401, affiche \"Identifiants "
                "incorrects\" SANS rediriger. Si la réponse est 429, affiche "
                "\"Trop de tentatives, réessayez plus tard\" SANS rediriger. Si "
                "le fetch échoue entièrement (backend non lancé), affiche "
                "\"Backend indisponible, lancez le serveur FastAPI\" SANS "
                "rediriger.\n\n"
                f"{_CONSIGNE_RENDU_DEMO}"
            ),
            required_resource_names=["business_rules.md"],
        ),
  "generate_dashboard": PromptTemplate(
            name="generate_dashboard",
            description="Génère le tableau de bord principal, connecté au vrai backend (lecture ET écriture)",
            template_text=(
                'Génère le code du tableau de bord (dashboard) "{page_name}".\n\n'
                "LECTURE : ce dashboard doit récupérer les VRAIES données via "
                "un appel fetch() en JavaScript vanilla vers "
                "http://localhost:8000/api/v1/budget/status (méthode GET), qui "
                "renvoie un objet JSON où chaque clé est un identifiant de "
                "projet et la valeur contient current_spend et budget_limit. "
                "N'invente AUCUNE donnée statique -- affiche uniquement ce que "
                "l'API retourne réellement. Calcule le ratio côté client "
                "(current_spend / budget_limit) pour styliser chaque ligne selon "
                "les règles métier ci-dessous.\n\n"
                "ÉCRITURE (simulateur réel) : pour chaque projet, ajoute un "
                "champ numérique (coût estimé, valeur par défaut 5) et un "
                "bouton 'Simuler un appel API'. Au clic, envoie une VRAIE "
                "requête POST à http://localhost:8000/api/v1/budget/check avec "
                "le corps JSON {{\"project_id\": \"...\", \"estimated_cost\": ...}}. "
                "Si la réponse est un succès (200), recharge immédiatement les "
                "vraies données via un nouvel appel GET à /status pour "
                "rafraîchir l'affichage avec l'état réellement mis à jour "
                "(ne modifie jamais les chiffres toi-même en JavaScript, "
                "affiche uniquement ce que le serveur renvoie après coup). Si "
                "le serveur renvoie une erreur 403 (budget bloqué), affiche "
                "clairement le message d'erreur renvoyé par l'API dans "
                "l'interface, sans casser la page.\n\n"
                "Si l'appel fetch échoue entièrement (ex: backend non lancé), "
                "affiche un message clair \"Backend indisponible, lancez le "
                "serveur FastAPI\" plutôt qu'une page cassée ou vide.\n\n"
                f"{_CONSIGNE_RENDU_DEMO}"
            ),
            required_resource_names=["project_context.md", "business_rules.md"],
       
        ),
        "generate_navbar": PromptTemplate(
            name="generate_navbar",
            description="Génère la barre de navigation du projet",
            template_text=(
                'Génère le code de la barre de navigation "{page_name}", '
                "cohérente avec le contexte du projet et les conventions "
                "de code ci-dessous.\n\n"
                f"{_CONSIGNE_RENDU_DEMO}"
            ),
            required_resource_names=["project_context.md", "coding_guidelines.md"],
        ),
      "generate_backend": PromptTemplate(
            name="generate_backend",
            description="Génère un endpoint backend FastAPI avec vraie logique métier",
            template_text=(
                'Génère le module backend "{page_name}", en respectant '
                "STRICTEMENT et RÉELLEMENT les règles métier ci-dessous "
                "(vérifications concrètes dans le code, pas juste mentionnées "
                "en commentaire).\n\n"
                "Implémente OBLIGATOIREMENT ces deux routes précises, pas plus, "
                "pas moins :\n"
                "1. POST /api/v1/budget/check -- vérifie et enregistre un "
                "nouvel appel API (paramètres : project_id, estimated_cost), "
                "applique les règles de seuil (alerte, blocage 403).\n"
                "2. GET /api/v1/budget/status -- renvoie l'état actuel de "
                "TOUS les projets (dictionnaire project_id -> current_spend, "
                "budget_limit), sans aucune vérification, juste la lecture "
                "de l'état actuel.\n\n"
                f"{_CONSIGNE_BACKEND}"
            ),
            required_resource_names=["project_context.md", "business_rules.md"],
        ),
        "generate_auth_backend": PromptTemplate(
            name="generate_auth_backend",
            description="Génère un backend d'authentification avec rôles réels",
            template_text=(
                'Génère le backend d\'authentification pour "{page_name}", '
                "avec des rôles cohérents avec le contexte du projet ci-dessous.\n\n"
                f"{_CONSIGNE_AUTH_BACKEND}"
            ),
            required_resource_names=["project_context.md"],
        ),
    
    }