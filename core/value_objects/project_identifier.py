"""Value object représentant l'identifiant valide d'un projet généré."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectIdentifier:
    """
    Un value object valide un invariant à la construction : ici, le nom
    du projet doit être un slug propre (minuscules, chiffres, tirets),
    pour éviter des noms de dossiers invalides ou dangereux.
    """

    value: str

    def __post_init__(self):
        if not re.match(r"^[a-z0-9][a-z0-9\-]*$", self.value):
            raise ValueError(
                f"Identifiant de projet invalide : '{self.value}'. "
                "Utilise uniquement minuscules, chiffres et tirets (ex: 'aegisai')."
            )

    def __str__(self) -> str:
        return self.value