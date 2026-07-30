"""
Entité représentant un plan d'exécution -- un artefact RÉEL et CONTRÔLÉ,
jamais juste une réponse texte du LLM. Le LLM ne peut que le PROPOSER
(via create_plan) ; seul le backend, sur action explicite de l'utilisateur
dans l'interface, peut le faire passer à APPROVED puis EXECUTED.
"""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanStatus(str, Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"            # une étape a échoué, exécution arrêtée, pas de faux succès
    REJECTED = "rejected"
    INVALIDATED = "invalidated"  # le projet a changé entre création et exécution
    EXPIRED = "expired"          # un nouveau plan a remplacé celui-ci


@dataclass
class PlanStep:
    """Une étape concrète du plan -- ses arguments sont FIGÉS à la création, jamais régénérés."""

    step_id: str
    action_type: str
    target: str
    description: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionPlan:
    """Le plan complet : la demande, ce qui a été vérifié, les étapes prévues, son statut."""

    plan_id: str
    project_name: str
    user_request: str
    resources_consulted: List[str]
    duplication_check: str
    steps: List[PlanStep]
    project_state_hash: Dict[str, str]
    status: PlanStatus = PlanStatus.PENDING_CONFIRMATION
    created_at: str = ""

    def to_dict(self) -> dict:
        donnees = asdict(self)
        donnees["status"] = self.status.value
        return donnees

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, donnees: dict) -> "ExecutionPlan":
        steps = [PlanStep(**s) for s in donnees["steps"]]
        return cls(
            plan_id=donnees["plan_id"],
            project_name=donnees["project_name"],
            user_request=donnees["user_request"],
            resources_consulted=donnees["resources_consulted"],
            duplication_check=donnees["duplication_check"],
            steps=steps,
            project_state_hash=donnees["project_state_hash"],
            status=PlanStatus(donnees["status"]),
            created_at=donnees.get("created_at", ""),
        )