"""
Préférences utilisateur d'un Workspace -- paires clé/valeur simples
(ex: run_tests_before_push, architecture_style), persistées en JSON,
lues par les tools/services concernés (ex: PlanExecutorService) pour
adapter leur comportement sans modification de code.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class WorkspacePreferences:
    """Un simple magasin clé/valeur de préférences, propre à un Workspace."""

    values: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.values.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def to_dict(self) -> dict:
        return dict(self.values)

    @staticmethod
    def from_dict(donnees: dict) -> "WorkspacePreferences":
        return WorkspacePreferences(values=dict(donnees))