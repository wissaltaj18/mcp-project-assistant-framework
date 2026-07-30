"""
Agent conversationnel utilisant Ollama en local (Qwen2.5/Qwen3), avec
le vrai tool calling natif de l'API Ollama -- alternative à Gemini, sans
dépendre d'un quota externe. Le format des tools suit la même convention
qu'OpenAI (compatible avec Ollama), construit à partir des mêmes
TOOL_SCHEMAS que Gemini pour ne jamais dupliquer les définitions.
"""

from typing import List, Dict, Any

import requests

from core.ports.conversational_agent_port import ConversationalAgentPort
from config.llm_config import LLMConfig
from services.chat_tools import ChatTools
from services.tool_schemas import TOOL_SCHEMAS, SYSTEM_INSTRUCTION
from services.tool_dispatch import build_dispatch


def _construire_tools_ollama() -> List[dict]:
    """Convertit TOOL_SCHEMAS au format attendu par l'API Ollama (identique à OpenAI)."""
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["parameters"],
            },
        }
        for s in TOOL_SCHEMAS
    ]


class OllamaChatAgent(ConversationalAgentPort):
    """Implémentation concrète : conversation avec mémoire, via Ollama, tool calling natif."""

    def __init__(self, config: LLMConfig, chat_tools: ChatTools):
        self._config = config
        self._dispatch = build_dispatch(chat_tools)
        self._tools_ollama = _construire_tools_ollama()
        self._historique: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_INSTRUCTION}]

    def chat(self, message: str) -> str:
        reponse, _ = self.chat_with_trace(message)
        return reponse

    def chat_with_trace(self, message: str) -> "tuple[str, List[Dict[str, Any]]]":
        self._historique.append({"role": "user", "content": message})
        trace: List[Dict[str, Any]] = []

        while True:
            reponse_json = self._appeler_ollama()
            message_reponse = reponse_json.get("message", {})
            appels = message_reponse.get("tool_calls") or []

            if not appels:
                contenu = message_reponse.get("content", "")
                self._historique.append({"role": "assistant", "content": contenu})
                return contenu, trace

            self._historique.append(message_reponse)

            for appel in appels:
                fonction_info = appel.get("function", {})
                nom = fonction_info.get("name")
                args = fonction_info.get("arguments") or {}
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
                self._historique.append({"role": "tool", "content": str(resultat)})

    def _appeler_ollama(self) -> dict:
        url = f"{self._config.base_url}/api/chat"
        try:
            reponse = requests.post(
                url,
                json={
                    "model": self._config.model_name,
                    "messages": self._historique,
                    "tools": self._tools_ollama,
                    "stream": False,
                },
                timeout=self._config.timeout_seconds,
            )
        except requests.RequestException as e:
            raise ConnectionError(
                f"Impossible de joindre Ollama à {self._config.base_url}. Est-il lancé ? Détail : {e}"
            )

        if reponse.status_code != 200:
            raise RuntimeError(f"Erreur Ollama (code {reponse.status_code}) : {reponse.text}")

        return reponse.json()

    def reset(self) -> None:
        """Réinitialise la conversation (historique vidé)."""
        self._historique = [{"role": "system", "content": SYSTEM_INSTRUCTION}]