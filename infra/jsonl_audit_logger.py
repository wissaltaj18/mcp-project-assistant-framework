"""
Implémentation concrète d'AuditLogPort : un fichier JSONL (JSON Lines) --
une ligne = un événement, jamais réécrit, jamais supprimé. Choix
pragmatique : lisible, inspectable à l'oeil, aucune dépendance externe,
mais l'interface AuditLogPort permet de basculer vers une vraie base
d'audit plus tard sans toucher aux appelants.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.ports.audit_log_port import AuditLogPort


class JsonlAuditLogger(AuditLogPort):
    """Journalise chaque action dans un fichier .jsonl, append-only."""

    def __init__(self, project_root: str):
        self._chemin = Path(project_root) / "audit_log.jsonl"

    def record(self, action: str, details: Dict[str, Any]) -> None:
        evenement = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
        }
        with open(self._chemin, "a", encoding="utf-8") as f:
            f.write(json.dumps(evenement, ensure_ascii=False) + "\n")