"""
Résultat d'une analyse FACTUELLE (aucun LLM) des règles de développement
d'un Workspace -- framework de tests, linter, CI, convention de nommage
observée, branche Git par défaut, présence/couverture du .gitignore.
Entité séparée d'ArchitectureAnalysisReport (Option B validée) : ce sont
des règles de dev, pas de l'architecture.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DevelopmentRulesReport:
    """Faits de règles de développement détectés -- déterministes, aucune interprétation."""

    test_framework: Optional[str] = None
    linter: Optional[str] = None
    ci_system: Optional[str] = None
    naming_convention: Optional[str] = None
    default_branch: Optional[str] = None
    gitignore_exists: bool = False
    gitignore_covers_env: bool = False

    def to_markdown_fragment(self) -> str:
        lignes = ["# Règles de développement (détection automatique)", ""]

        lignes.append("## Framework de tests")
        lignes.append(f"- {self.test_framework}" if self.test_framework else "Information non disponible.")

        lignes.append("")
        lignes.append("## Linter / outil de qualité de code")
        lignes.append(f"- {self.linter}" if self.linter else "Information non disponible.")

        lignes.append("")
        lignes.append("## Intégration continue (CI)")
        lignes.append(f"- {self.ci_system}" if self.ci_system else "Information non disponible.")

        lignes.append("")
        lignes.append("## Convention de nommage observée")
        lignes.append(f"- {self.naming_convention}" if self.naming_convention else "Information non disponible.")

        lignes.append("")
        lignes.append("## Branche Git par défaut")
        lignes.append(f"- {self.default_branch}" if self.default_branch else "Information non disponible.")

        lignes.append("")
        lignes.append("## Fichier .gitignore")
        if not self.gitignore_exists:
            lignes.append("Absent.")
        elif self.gitignore_covers_env:
            lignes.append("Présent, couvre les fichiers .env.")
        else:
            lignes.append("Présent, mais ne couvre pas explicitement .env -- à vérifier.")

        return "\n".join(lignes)