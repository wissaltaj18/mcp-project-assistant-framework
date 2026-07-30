"""
Agent conversationnel utilisant le function calling MANUEL de Gemini,
construit à partir des mêmes TOOL_SCHEMAS partagés que l'agent Ollama --
aucune duplication de définitions entre les deux providers.
"""

from typing import List, Dict, Any

from google import genai
from google.genai import types

from core.ports.conversational_agent_port import ConversationalAgentPort
from config.llm_config import GeminiConfig
from services.chat_tools import ChatTools
from services.tool_schemas import TOOL_SCHEMAS, SYSTEM_INSTRUCTION
from services.tool_dispatch import build_dispatch


def _construire_declarations_gemini() -> List[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(name=s["name"], description=s["description"], parameters=s["parameters"])
        for s in TOOL_SCHEMAS
    ]


class GeminiChatAgent(ConversationalAgentPort):
    """Implémentation concrète : conversation avec mémoire, via Gemini, function calling manuel."""

    def __init__(self, config: GeminiConfig, chat_tools: ChatTools):
        self._client = genai.Client(api_key=config.api_key)
        self._model_name = config.model_name
        self._dispatch = build_dispatch(chat_tools)
        self._config = types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=_construire_declarations_gemini())],
            system_instruction=SYSTEM_INSTRUCTION,
        )
        self._chat_session = None

    def _get_session(self):
        if self._chat_session is None:
            self._chat_session = self._client.chats.create(model=self._model_name, config=self._config)
        return self._chat_session

    def chat(self, message: str) -> str:
        reponse, _ = self.chat_with_trace(message)
        return reponse

    def chat_with_trace(self, message: str) -> "tuple[str, List[Dict[str, Any]]]":
        session = self._get_session()
        trace: List[Dict[str, Any]] = []

        reponse = session.send_message(message)

        while True:
            appels = getattr(reponse, "function_calls", None)
            if not appels:
                break

            parts_reponse = []
            for appel in appels:
                nom = appel.name
                args = dict(appel.args or {})
                trace.append({"type": "tool_call", "name": nom, "args": args})

                fonction = self._dispatch.get(nom)
                if fonction is None:
                    resultat = f"Tool inconnu : {nom}"
                else:
                    try:
                        resultat = fonction(**args)
                    except Exception as e:
                        resultat = f"Erreur lors de l'exécution de {nom} : {e}"

                trace.append({"type": "tool_result", "name": nom, "result": resultat})
                parts_reponse.append(types.Part.from_function_response(name=nom, response={"result": resultat}))

            reponse = session.send_message(parts_reponse)

        return reponse.text, trace

    def reset(self) -> None:
        """Réinitialise la conversation (nouvelle session, historique vidé)."""
        self._chat_session = None