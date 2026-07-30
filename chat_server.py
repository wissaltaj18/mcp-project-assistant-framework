# """
# Serveur de chat conversationnel du framework : l'utilisateur écrit sa
# demande en langage naturel, l'agent (Gemini, Ollama ou Claude, selon
# ACTIVE_LLM_PROVIDER) décide lui-même quelle action effectuer -- mais ne
# peut JAMAIS écrire directement. Sa seule capacité d'écriture est
# create_plan ; l'exécution réelle passe uniquement par les endpoints
# /api/v1/plans/{id}/approve|reject, jamais vus par le LLM.
# """

# import os

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel

# from bootstrap import build_container
# from config.llm_config import GeminiConfig, LLMConfig
# from services.chat_tools import ChatTools
# from llm.gemini_chat_agent import GeminiChatAgent
# from llm.ollama_chat_agent import OllamaChatAgent
# from llm.claude_chat_agent import ClaudeChatAgent

# PROJET_ACTIF = os.getenv("ACTIVE_PROJECT_NAME", "default-project")
# PROVIDER_ACTIF = os.getenv("ACTIVE_LLM_PROVIDER", "gemini")

# app = FastAPI(title="MCP Software Engineering Assistant")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# _container = build_container()
# _chat_tools = ChatTools(_container, project_name=PROJET_ACTIF)

# print(f">>> PROVIDER ACTIF DETECTE : {PROVIDER_ACTIF} <<<")

# if PROVIDER_ACTIF == "ollama_qwen":
#     _agent = OllamaChatAgent(LLMConfig.from_env(), _chat_tools)
# elif PROVIDER_ACTIF == "claude":
#     from config import credentials_store
#     _agent = ClaudeChatAgent(api_key=credentials_store.get("ANTHROPIC_API_KEY"), chat_tools=_chat_tools)
# else:
#     _agent = GeminiChatAgent(GeminiConfig.from_env(), _chat_tools)


# class ChatRequest(BaseModel):
#     message: str


# class ChatResponse(BaseModel):
#     reply: str
#     steps: list = []
#     project: str = PROJET_ACTIF


# @app.post("/api/v1/chat", response_model=ChatResponse)
# def chat(request: ChatRequest):
#     try:
#         reponse, trace = _agent.chat_with_trace(request.message)
#     except Exception as e:
#         message_erreur = str(e)
#         if "RESOURCE_EXHAUSTED" in message_erreur or "429" in message_erreur:
#             return ChatResponse(
#                 reply="Quota temporairement dépassé. Attends environ 30 à 60 secondes puis réessaie.",
#                 steps=[], project=PROJET_ACTIF,
#             )
#         return ChatResponse(
#             reply=f"Erreur inattendue côté serveur : {message_erreur[:200]}",
#             steps=[], project=PROJET_ACTIF,
#         )
#     return ChatResponse(reply=reponse, steps=trace, project=PROJET_ACTIF)


# @app.get("/api/v1/active-project")
# def get_active_project():
#     return {"project": PROJET_ACTIF}


# @app.get("/api/v1/project-info")
# def get_project_info():
#     return {
#         "project": PROJET_ACTIF,
#         "resources": _container.resource_service.list_project_resources(PROJET_ACTIF),
#         "generators": _container.prompt_service.list_available_prompts(),
#     }


# @app.get("/api/v1/settings")
# def get_settings():
#     """Renvoie quels identifiants sont configurés (jamais leur vraie valeur)."""
#     from config import credentials_store
#     return credentials_store.list_configured_keys()


# class SettingsUpdate(BaseModel):
#     key: str
#     value: str


# @app.post("/api/v1/settings")
# def update_settings(update: SettingsUpdate):
#     """Enregistre un identifiant (clé API, token) depuis l'interface -- jamais un terminal."""
#     from config import credentials_store
#     credentials_store.set_credential(update.key, update.value)
#     return {"status": "ok"}


# _plan_storage = None
# _plan_executor = None


# def _get_plan_storage():
#     global _plan_storage
#     if _plan_storage is None:
#         from services.plan_storage_service import PlanStorageService
#         _plan_storage = PlanStorageService(_chat_tools._chemin_projet_complet)
#     return _plan_storage


# def _get_plan_executor():
#     global _plan_executor
#     if _plan_executor is None:
#         from services.plan_executor_service import PlanExecutorService
#         _plan_executor = PlanExecutorService(_container, _get_plan_storage(), _chat_tools)
#     return _plan_executor


# @app.get("/api/v1/plans/{plan_id}")
# def get_plan(plan_id: str):
#     """
#     Consulte un plan -- endpoint HTTP classique, JAMAIS appelé par le LLM
#     (absent de TOOL_SCHEMAS). C'est ce que chat.html appelle pour afficher
#     le plan complet avant que l'utilisateur décide.
#     """
#     plan = _get_plan_storage().load(plan_id)
#     if plan is None:
#         return {"error": f"Plan '{plan_id}' introuvable."}
#     return plan.to_dict()


# @app.post("/api/v1/plans/{plan_id}/approve")
# def approve_plan(plan_id: str):
#     """
#     Déclenche l'EXÉCUTION RÉELLE d'un plan -- appelé UNIQUEMENT par un clic
#     utilisateur dans l'interface (fetch direct depuis chat.html). Ce chemin
#     ne passe JAMAIS par le LLM ni par la conversation -- c'est la séparation
#     structurelle exigée : le LLM ne peut jamais s'auto-approuver.
#     """
#     return _get_plan_executor().execute(plan_id, PROJET_ACTIF)


# @app.post("/api/v1/plans/{plan_id}/reject")
# def reject_plan(plan_id: str):
#     """Rejette un plan -- appelé uniquement par un clic utilisateur, jamais par le LLM."""
#     return _get_plan_executor().reject(plan_id)


# @app.post("/api/v1/reset")
# def reset_conversation():
#     _agent.reset()
#     return {"status": "ok"}


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8080)
"""
Serveur de chat conversationnel du framework : l'utilisateur écrit sa
demande en langage naturel, l'agent (Gemini, Ollama ou Claude, selon
ACTIVE_LLM_PROVIDER) décide lui-même quelle action effectuer -- mais ne
peut JAMAIS écrire directement. Sa seule capacité d'écriture est
create_plan ; l'exécution réelle passe uniquement par les endpoints
/api/v1/plans/{id}/approve|reject, jamais vus par le LLM.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bootstrap import build_container
from config.llm_config import GeminiConfig, LLMConfig
from services.chat_tools import ChatTools
from llm.gemini_chat_agent import GeminiChatAgent
from llm.ollama_chat_agent import OllamaChatAgent
from llm.claude_chat_agent import ClaudeChatAgent

PROJET_ACTIF = os.getenv("ACTIVE_PROJECT_NAME", "default-project")
PROVIDER_ACTIF = os.getenv("ACTIVE_LLM_PROVIDER", "gemini")

app = FastAPI(title="MCP Software Engineering Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_container = build_container()
_chat_tools = ChatTools(_container, project_name=PROJET_ACTIF)

print(f">>> PROVIDER ACTIF DETECTE : {PROVIDER_ACTIF} <<<")

if PROVIDER_ACTIF == "ollama_qwen":
    _agent = OllamaChatAgent(LLMConfig.from_env(), _chat_tools)
elif PROVIDER_ACTIF == "claude":
    from config import credentials_store
    _agent = ClaudeChatAgent(api_key=credentials_store.get("ANTHROPIC_API_KEY"), chat_tools=_chat_tools)
else:
    _agent = GeminiChatAgent(GeminiConfig.from_env(), _chat_tools)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    steps: list = []
    project: str = PROJET_ACTIF


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        reponse, trace = _agent.chat_with_trace(request.message)
        # Diagnostic gratuit -- affiche juste ce qui a déjà été reçu,
        # aucun appel réseau supplémentaire, aucun coût de quota.
        for etape in trace:
            print(f">>> TRACE COMPLETE : {etape}")
    except Exception as e:
        message_erreur = str(e)
        if "RESOURCE_EXHAUSTED" in message_erreur or "429" in message_erreur:
            return ChatResponse(
                reply="Quota temporairement dépassé. Attends environ 30 à 60 secondes puis réessaie.",
                steps=[], project=PROJET_ACTIF,
            )
        return ChatResponse(
            reply=f"Erreur inattendue côté serveur : {message_erreur[:200]}",
            steps=[], project=PROJET_ACTIF,
        )
    return ChatResponse(reply=reponse, steps=trace, project=PROJET_ACTIF)


@app.get("/api/v1/active-project")
def get_active_project():
    return {"project": PROJET_ACTIF}


@app.get("/api/v1/project-info")
def get_project_info():
    return {
        "project": PROJET_ACTIF,
        "resources": _container.resource_service.list_project_resources(PROJET_ACTIF),
        "generators": _container.prompt_service.list_available_prompts(),
    }


@app.get("/api/v1/settings")
def get_settings():
    """Renvoie quels identifiants sont configurés (jamais leur vraie valeur)."""
    from config import credentials_store
    return credentials_store.list_configured_keys()


class SettingsUpdate(BaseModel):
    key: str
    value: str


@app.post("/api/v1/settings")
def update_settings(update: SettingsUpdate):
    """Enregistre un identifiant (clé API, token) depuis l'interface -- jamais un terminal."""
    from config import credentials_store
    credentials_store.set_credential(update.key, update.value)
    return {"status": "ok"}


_plan_storage = None
_plan_executor = None


def _get_plan_storage():
    global _plan_storage
    if _plan_storage is None:
        from services.plan_storage_service import PlanStorageService
        _plan_storage = PlanStorageService(_chat_tools._chemin_projet_complet)
    return _plan_storage


def _get_plan_executor():
    global _plan_executor
    if _plan_executor is None:
        from services.plan_executor_service import PlanExecutorService
        _plan_executor = PlanExecutorService(_container, _get_plan_storage(), _chat_tools)
    return _plan_executor


@app.get("/api/v1/plans/{plan_id}")
def get_plan(plan_id: str):
    """
    Consulte un plan -- endpoint HTTP classique, JAMAIS appelé par le LLM
    (absent de TOOL_SCHEMAS). C'est ce que chat.html appelle pour afficher
    le plan complet avant que l'utilisateur décide.
    """
    plan = _get_plan_storage().load(plan_id)
    if plan is None:
        return {"error": f"Plan '{plan_id}' introuvable."}
    return plan.to_dict()


@app.post("/api/v1/plans/{plan_id}/approve")
def approve_plan(plan_id: str):
    """
    Déclenche l'EXÉCUTION RÉELLE d'un plan -- appelé UNIQUEMENT par un clic
    utilisateur dans l'interface (fetch direct depuis chat.html). Ce chemin
    ne passe JAMAIS par le LLM ni par la conversation -- c'est la séparation
    structurelle exigée : le LLM ne peut jamais s'auto-approuver.
    """
    return _get_plan_executor().execute(plan_id, PROJET_ACTIF)


@app.post("/api/v1/plans/{plan_id}/reject")
def reject_plan(plan_id: str):
    """Rejette un plan -- appelé uniquement par un clic utilisateur, jamais par le LLM."""
    return _get_plan_executor().reject(plan_id)


@app.post("/api/v1/reset")
def reset_conversation():
    _agent.reset()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)