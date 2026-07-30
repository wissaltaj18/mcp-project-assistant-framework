"""Validation basique du contenu d'une Resource (pas vide, structure minimale)."""

from core.entities.resource import Resource


class ResourceValidator:
    """
    Vérifie qu'une Resource chargée est utilisable. Ne valide pas le
    SENS métier du contenu (impossible à faire génériquement), juste
    sa structure minimale.
    """

    def validate(self, resource: Resource) -> list[str]:
        erreurs = []

        if resource.is_empty():
            erreurs.append(f"'{resource.name}' est vide.")
            return erreurs

        if not resource.content.strip().startswith("#"):
            erreurs.append(
                f"'{resource.name}' ne commence pas par un titre Markdown (#). "
                "Convention attendue pour toutes les Resources."
            )

        return erreurs