"""
Port pour un agent conversationnel : contrairement au LLMProviderPort
(un simple prompt -> texte), celui-ci gère une conversation où l'agent
décide LUI-MÊME quelle action interne exécuter, via function calling.
"""

from abc import ABC, abstractmethod


class ConversationalAgentPort(ABC):
    """Contrat pour un agent capable de décider et d'exécuter des actions."""

    @abstractmethod
    def chat(self, message: str) -> str:
        """
        Envoie un message utilisateur en langage naturel. L'agent décide
        lui-même s'il doit appeler un outil (lister les resources, générer
        du code...) avant de répondre.
        """
        raise NotImplementedError