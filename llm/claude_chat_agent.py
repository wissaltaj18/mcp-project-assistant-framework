"""
Agent conversationnel utilisant Claude (Anthropic), avec le tool calling
natif de l'API Messages. Construit à partir des mêmes TOOL_SCHEMAS
partagés que Gemini et Ollama -- troisième provider interchangeable,
aucune duplication de définitions.
"""

from typing import List, Dict, Any

import anthropic

from core.ports.conversational_agent_port import ConversationalAgentPort
from services.chat_tools import ChatTools
from services.tool_schemas import TOOL_SCHEMAS, SYSTEM_INSTRUCTION
from services.tool_dispatch import build_dispatch


def _construire_tools_claude() -> List[dict]:
    return [
        {"name": s["name"], "description": s["description"], "input_schema": s["parameters"]}
        for s in TOOL_SCHEMAS
    ]


class ClaudeChatAgent(ConversationalAgentPort):
    """Implémentation concrète : conversation avec mémoire, via Claude, tool calling natif."""

    def __init__(self, api_key: str, chat_tools: ChatTools, model_name: str = "claude-sonnet-4-5"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model_name = model_name
        self._tools_claude = _construire_tools_claude()
        self._dispatch = build_dispatch(chat_tools)
        self._historique: List[Dict[str, Any]] = []

    def chat(self, message: str) -> str:
        reponse, _ = self.chat_with_trace(message)
        return reponse

    def chat_with_trace(self, message: str) -> "tuple[str, List[Dict[str, Any]]]":
        self._historique.append({"role": "user", "content": message})
        trace: List[Dict[str, Any]] = []

        while True:
            reponse = self._client.messages.create(
                model=self._model_name,
                max_tokens=1024,
                system=SYSTEM_INSTRUCTION,
                messages=self._historique,
                tools=self._tools_claude,
            )

            blocs_outil = [b for b in reponse.content if b.type == "tool_use"]

            if not blocs_outil:
                texte = "".join(b.text for b in reponse.content if b.type == "text")
                self._historique.append({"role": "assistant", "content": reponse.content})
                return texte, trace

            self._historique.append({"role": "assistant", "content": reponse.content})

            resultats_outils = []
            for bloc in blocs_outil:
                nom = bloc.name
                args = bloc.input or {}
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
                resultats_outils.append({
                    "type": "tool_result",
                    "tool_use_id": bloc.id,
                    "content": str(resultat),
                })

            self._historique.append({"role": "user", "content": resultats_outils})

    def reset(self) -> None:
        """Réinitialise la conversation (historique vidé)."""
        self._historique = []