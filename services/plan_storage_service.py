"""
Stockage des plans d'exécution -- un fichier JSON par plan, sous
.plans/{plan_id}.json à la racine du projet. Persiste même si le serveur
redémarre (contrairement à l'ancien _pending_actions en mémoire, faille
identifiée dans l'audit). Simple, inspectable, aucune dépendance externe.
"""

from pathlib import Path
from typing import Optional

from core.entities.execution_plan import ExecutionPlan, PlanStatus


class PlanStorageService:
    """Cas d'usage : sauvegarder, charger, et mettre à jour le statut d'un plan."""

    def __init__(self, project_root: str):
        self._dossier_plans = Path(project_root) / ".plans"
        self._dossier_plans.mkdir(parents=True, exist_ok=True)

    def _chemin(self, plan_id: str) -> Path:
        return self._dossier_plans / f"{plan_id}.json"

    def save(self, plan: ExecutionPlan) -> None:
        self._chemin(plan.plan_id).write_text(plan.to_json(), encoding="utf-8")

    def load(self, plan_id: str) -> Optional[ExecutionPlan]:
        chemin = self._chemin(plan_id)
        if not chemin.exists():
            return None
        import json
        return ExecutionPlan.from_dict(json.loads(chemin.read_text(encoding="utf-8")))

    def update_status(self, plan_id: str, nouveau_statut: PlanStatus) -> Optional[ExecutionPlan]:
        plan = self.load(plan_id)
        if plan is None:
            return None
        plan.status = nouveau_statut
        self.save(plan)
        return plan

    def expire_previous_pending_plans(self, project_name: str) -> None:
        """Si un nouveau plan est créé, les anciens plans encore en attente deviennent EXPIRED."""
        import json
        for fichier in self._dossier_plans.glob("*.json"):
            donnees = json.loads(fichier.read_text(encoding="utf-8"))
            if donnees.get("status") == PlanStatus.PENDING_CONFIRMATION.value:
                donnees["status"] = PlanStatus.EXPIRED.value
                fichier.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")