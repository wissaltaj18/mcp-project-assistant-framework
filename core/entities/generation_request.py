"""Entité représentant une demande de génération de code (le 'ordre' donné à l'agent)."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class GenerationRequest:
    """
    Une demande complète : quel projet, quel prompt utiliser, avec
    quels arguments. C'est ce que reçoit l'agent avant de lancer le
    cycle Resources -> Prompt -> LLM -> Fichier.
    """

    project_name: str
    prompt_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        return f"[{self.project_name}] Prompt '{self.prompt_name}' avec {self.arguments}"