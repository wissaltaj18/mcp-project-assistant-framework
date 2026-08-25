"""
Crée les templates manuels (engineering_principles.md,
architecture_philosophy.md) une seule fois -- jamais écrasés
si le fichier existe déjà sur le disque.
"""

from pathlib import Path

_HEADER = """\
<!--
  Ce fichier a été créé automatiquement par la plateforme MCP.
  Il est généré UNE SEULE FOIS et ne sera JAMAIS écrasé automatiquement.
  Vous êtes libre de le modifier, enrichir et faire évoluer.
  C'est la mémoire vivante de votre projet.
-->

"""

ENGINEERING_PRINCIPLES_TEMPLATE = _HEADER + """\
# Engineering Principles

## Vision
<!-- Décrivez en quelques phrases la philosophie générale de votre équipe. -->
_À compléter_

## CONSTRAINTS — Principes non négociables
- Exemple : Aucun secret dans le code source.
- Exemple : Toute modification passe par une Pull Request reviewée.

## PREFERENCES — Bonnes pratiques privilégiées
- Exemple : Favoriser la composition sur l'héritage.
- Exemple : Préférer les interfaces étroites aux interfaces larges.

## ANTI_PATTERNS — Ce que vous évitez
- Exemple : Pas de logique métier dans les Controllers.
- Exemple : Pas de couplage fort entre les modules.
"""

ARCHITECTURE_PHILOSOPHY_TEMPLATE = _HEADER + """\
# Architecture Philosophy

## Patterns retenus
<!-- Quels patterns architecturaux avez-vous choisis et pourquoi ? -->
_À compléter_

## Décisions d'architecture
- Exemple : Choix de Symfony pour la maturité de l'écosystème PHP.
- Exemple : Séparation stricte Controller / Service / Repository.

## Compromis assumés
_À compléter_

## Ce qui ne doit pas changer
_À compléter_
"""


class TemplateResourceService:
    """
    Crée les fichiers templates si et seulement si ils n'existent pas.
    Ne touche jamais à un fichier existant.
    """

    TEMPLATES = {
        "engineering_principles.md": ENGINEERING_PRINCIPLES_TEMPLATE,
        "architecture_philosophy.md": ARCHITECTURE_PHILOSOPHY_TEMPLATE,
    }

    def create_if_absent(self, resources_dir: str) -> list:
        """
        Crée les templates absents dans resources_dir.
        Retourne la liste des fichiers effectivement créés.
        """
        crees = []
        dossier = Path(resources_dir)
        dossier.mkdir(parents=True, exist_ok=True)

        for nom_fichier, contenu in self.TEMPLATES.items():
            chemin = dossier / nom_fichier
            if not chemin.exists():
                chemin.write_text(contenu, encoding="utf-8")
                crees.append(nom_fichier)

        return crees