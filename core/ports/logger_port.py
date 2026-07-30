"""
Port pour journaliser ce que fait le framework (utile pour déboguer
le vibe coding : quel tool a été appelé, quel prompt envoyé au LLM...).
"""

from abc import ABC, abstractmethod


class LoggerPort(ABC):
    """Contrat pour tout composant de journalisation utilisé par le framework."""

    @abstractmethod
    def info(self, message: str) -> None:
        """Journalise une information normale (ex: 'Tool create_file exécuté')."""
        raise NotImplementedError

    @abstractmethod
    def error(self, message: str) -> None:
        """Journalise une erreur (ex: 'Resource introuvable')."""
        raise NotImplementedError