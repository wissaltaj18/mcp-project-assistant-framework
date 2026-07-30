"""Entité représentant la définition d'un Tool (pas son exécution)."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class ToolDefinition:
    """
    Décrit un Tool : son nom, sa description, et le schéma de ses paramètres
    attendus. Ne contient AUCUNE logique d'exécution -- juste la définition,
    utile pour la découverte (équivalent de list_tools en MCP).
    """

    name: str
    description: str
    parameters_schema: Dict[str, Any] = field(default_factory=dict)

    def validate_arguments(self, arguments: Dict[str, Any]) -> list[str]:
        """
        Vérifie que les arguments fournis contiennent bien les champs
        requis par le schéma. Renvoie la liste des erreurs (vide si tout va bien).
        """
        erreurs = []
        requis = self.parameters_schema.get("required", [])
        for champ in requis:
            if champ not in arguments:
                erreurs.append(f"Argument obligatoire manquant : '{champ}'")
        return erreurs