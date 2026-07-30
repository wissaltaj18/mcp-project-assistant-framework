"""
Port (interface abstraite) que TOUT fournisseur de LLM doit respecter.

Aucune implémentation concrète ici -- juste le contrat. services/ et agents/
ne dépendent que de cette interface, jamais d'une implémentation précise
(Ollama, Claude, Gemini...). C'est le coeur du Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod


class LLMProviderPort(ABC):
    """Contrat qu'un fournisseur de LLM (Ollama/Qwen, ou autre demain) doit implémenter."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Envoie un prompt au LLM et renvoie le texte généré.

        Args:
            prompt: Le texte complet à envoyer au modèle
            max_tokens: Nombre maximum de tokens à générer en réponse

        Returns:
            Le texte généré par le modèle
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie que le LLM est joignable (ex: Ollama est lancé et répond).
        Permet de donner une erreur claire avant d'essayer de générer du code.
        """
        raise NotImplementedError