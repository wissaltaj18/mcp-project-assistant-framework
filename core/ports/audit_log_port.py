"""Port pour journaliser les actions de l'agent -- traçabilité réelle."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class AuditLogPort(ABC):
    """Contrat pour tout composant capable d'enregistrer une action de façon durable."""

    @abstractmethod
    def record(self, action: str, details: Dict[str, Any]) -> None:
        """Enregistre une action horodatée, de façon permanente (append-only)."""
        raise NotImplementedError