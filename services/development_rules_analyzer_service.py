"""
Analyse FACTUELLE (déterministe, aucun LLM) des règles de développement
d'un Workspace : framework de tests, linter, CI, convention de nommage
observée par échantillonnage réel, branche Git par défaut, .gitignore.
Réutilise ArchitectureAnalyzerService pour connaître les langages
présents (Option A/B, même patron que FunctionalOverviewAnalyzerService).
"""

import subprocess
from pathlib import Path
from typing import Optional

from core.entities.development_rules_report import DevelopmentRulesReport
from services.architecture_analyzer_service import ArchitectureAnalyzerService, EXTENSIONS_VERS_LANGAGE

DOSSIERS_A_IGNORER = {
    "vendor", "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "target", "bin", "obj", "tests", "test",
}

MAX_FICHIERS_ECHANTILLONNES = 200


class DevelopmentRulesAnalyzerService:
    """Cas d'usage : produire un rapport factuel des règles de développement d'un Workspace."""

    def __init__(self, architecture_analyzer: Optional[ArchitectureAnalyzerService] = None):
        self._architecture_analyzer = architecture_analyzer or ArchitectureAnalyzerService()

    def analyze(self, repo_path: str) -> DevelopmentRulesReport:
        racine = Path(repo_path)
        if not racine.exists():
            return DevelopmentRulesReport()

        gitignore_existe, gitignore_couvre_env = self._verifier_gitignore(racine)

        return DevelopmentRulesReport(
            test_framework=self._detecter_framework_de_tests(racine),
            linter=self._detecter_linter(racine),
            ci_system=self._detecter_ci(racine),
            naming_convention=self._detecter_convention_de_nommage(racine),
            default_branch=self._detecter_branche_par_defaut(racine),
            gitignore_exists=gitignore_existe,
            gitignore_covers_env=gitignore_couvre_env,
        )

    def _detecter_framework_de_tests(self, racine: Path) -> Optional[str]:
        if (racine / "phpunit.xml").exists() or (racine / "phpunit.xml.dist").exists():
            return "PHPUnit"
        if (racine / "pytest.ini").exists():
            return "pytest"
        pyproject = racine / "pyproject.toml"
        if pyproject.exists():
            try:
                if "[tool.pytest" in pyproject.read_text(encoding="utf-8", errors="ignore"):
                    return "pytest"
            except OSError:
                pass
        if (racine / "jest.config.js").exists() or (racine / "jest.config.ts").exists():
            return "Jest"
        return None

    def _detecter_linter(self, racine: Path) -> Optional[str]:
        if list(racine.glob(".eslintrc*")):
            return "ESLint"
        if (racine / "phpcs.xml").exists():
            return "PHP_CodeSniffer"
        if (racine / "ruff.toml").exists() or (racine / ".ruff.toml").exists():
            return "Ruff"
        if (racine / ".flake8").exists():
            return "Flake8"
        return None

    def _detecter_ci(self, racine: Path) -> Optional[str]:
        dossier_workflows = racine / ".github" / "workflows"
        if dossier_workflows.exists() and any(dossier_workflows.iterdir()):
            return "GitHub Actions"
        if (racine / ".gitlab-ci.yml").exists():
            return "GitLab CI"
        if (racine / ".circleci").exists():
            return "CircleCI"
        return None

    def _classifier_nom_fichier(self, stem: str) -> Optional[str]:
        """Classification purement mécanique -- pas d'interprétation, juste des motifs de caractères."""
        if not stem or not stem[0].isalpha():
            return None
        if "_" in stem:
            return "snake_case"
        if "-" in stem:
            return "kebab-case"
        if stem[0].isupper():
            return "PascalCase"
        if any(c.isupper() for c in stem):
            return "camelCase"
        return None

    def _detecter_convention_de_nommage(self, racine: Path) -> Optional[str]:
        rapport_architecture = self._architecture_analyzer.analyze(str(racine))
        extensions_presentes = {
            ext for ext, langage in EXTENSIONS_VERS_LANGAGE.items()
            if langage in rapport_architecture.languages
        }
        if not extensions_presentes:
            return None

        comptages: dict = {}
        exemples: dict = {}
        nb_scannes = 0

        for fichier in racine.rglob("*"):
            if nb_scannes >= MAX_FICHIERS_ECHANTILLONNES:
                break
            if not fichier.is_file() or fichier.suffix not in extensions_presentes:
                continue
            if any(partie in DOSSIERS_A_IGNORER for partie in fichier.parts):
                continue
            nb_scannes += 1
            classification = self._classifier_nom_fichier(fichier.stem)
            if classification is None:
                continue
            comptages[classification] = comptages.get(classification, 0) + 1
            exemples.setdefault(classification, fichier.name)

        if not comptages:
            return None

        convention_majoritaire = max(comptages, key=comptages.get)
        return f"{convention_majoritaire} (ex: {exemples[convention_majoritaire]})"

    def _detecter_branche_par_defaut(self, racine: Path) -> Optional[str]:
        try:
            resultat = subprocess.run(
                ["git", "-C", str(racine), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if resultat.returncode != 0:
            return None
        branche = resultat.stdout.strip()
        if not branche or branche == "HEAD":
            return None
        return branche

    def _verifier_gitignore(self, racine: Path) -> "tuple[bool, bool]":
        chemin = racine / ".gitignore"
        if not chemin.exists():
            return False, False
        try:
            contenu = chemin.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return True, False
        return True, ".env" in contenu