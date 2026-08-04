"""
Analyse fonctionnelle FACTUELLE (déterministe, aucun LLM) d'un
Workspace : cite la description des manifestes, un extrait du README,
les dossiers présents, un fichier de routes trouvé, et les entités
détectées -- ne synthétise ni n'invente jamais rien. Réutilise
ArchitectureAnalyzerService pour localiser les dossiers d'entités,
plutôt que de dupliquer cette détection (Option A validée).
"""

import json
from pathlib import Path
from typing import List, Optional

from core.entities.functional_overview_report import FunctionalOverviewReport
from services.architecture_analyzer_service import ArchitectureAnalyzerService

DOSSIERS_A_IGNORER = {
    "vendor", "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "target", "bin", "obj",
}

MOTIFS_DOSSIERS_COURANTS = [
    "controller", "controllers", "service", "services",
    "route", "routes", "entity", "entities", "model", "models",
]

FICHIERS_ROUTES_CANDIDATS = [
    "routes/web.php", "routes/api.php", "urls.py", "src/routes.js",
    "src/routes.ts", "config/routes.yaml",
]

TAILLE_MAX_EXTRAIT = 500


class FunctionalOverviewAnalyzerService:
    """Cas d'usage : produire un rapport fonctionnel factuel, en citant uniquement ce qui existe déjà dans le dépôt."""

    def __init__(self, architecture_analyzer: Optional[ArchitectureAnalyzerService] = None):
        self._architecture_analyzer = architecture_analyzer or ArchitectureAnalyzerService()

    def analyze(self, repo_path: str) -> FunctionalOverviewReport:
        racine = Path(repo_path)
        if not racine.exists():
            return FunctionalOverviewReport()

        return FunctionalOverviewReport(
            description=self._lire_description_manifeste(racine),
            readme_excerpt=self._lire_extrait_readme(racine),
            top_level_folders=self._lister_dossiers_principaux(racine),
            pattern_matched_folders=self._detecter_dossiers_par_motif(racine),
            detected_routes=self._lire_fichier_routes(racine),
            detected_entities=self._lister_entites(racine),
        )

    def _lire_json(self, chemin: Path) -> "dict | None":
        try:
            return json.loads(chemin.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            return None

    def _lire_description_manifeste(self, racine: Path) -> Optional[str]:
        for nom_fichier in ("composer.json", "package.json"):
            chemin = racine / nom_fichier
            if not chemin.exists():
                continue
            donnees = self._lire_json(chemin)
            if donnees and donnees.get("description"):
                return str(donnees["description"]).strip()
        return None

    def _lire_extrait_readme(self, racine: Path) -> Optional[str]:
        for nom_candidat in ("README.md", "readme.md", "Readme.md", "README.MD"):
            chemin = racine / nom_candidat
            if chemin.exists():
                try:
                    contenu = chemin.read_text(encoding="utf-8", errors="ignore").strip()
                except OSError:
                    continue
                if not contenu:
                    continue
                return contenu[:TAILLE_MAX_EXTRAIT]
        return None

    def _lister_dossiers_principaux(self, racine: Path) -> List[str]:
        try:
            return sorted(
                f.name for f in racine.iterdir()
                if f.is_dir() and f.name not in DOSSIERS_A_IGNORER and not f.name.startswith(".")
            )
        except OSError:
            return []

    def _detecter_dossiers_par_motif(self, racine: Path) -> List[str]:
        trouves = []
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(partie in DOSSIERS_A_IGNORER for partie in dossier.parts):
                continue
            if dossier.name.lower() in MOTIFS_DOSSIERS_COURANTS:
                trouves.append(str(dossier.relative_to(racine)))
        return sorted(trouves)

    def _lire_fichier_routes(self, racine: Path) -> Optional[str]:
        for candidat in FICHIERS_ROUTES_CANDIDATS:
            chemin = racine / candidat
            if chemin.exists():
                try:
                    contenu = chemin.read_text(encoding="utf-8", errors="ignore").strip()
                except OSError:
                    continue
                if contenu:
                    return f"({candidat})\n\n{contenu[:TAILLE_MAX_EXTRAIT]}"
        return None

    def _lister_entites(self, racine: Path) -> List[str]:
        rapport_architecture = self._architecture_analyzer.analyze(str(racine))
        dossiers_entites = rapport_architecture.layer_folders.get("entity", [])

        noms_entites = set()
        for chemin_relatif in dossiers_entites:
            dossier_absolu = racine / chemin_relatif
            if not dossier_absolu.is_dir():
                continue
            for fichier in dossier_absolu.iterdir():
                if fichier.is_file() and fichier.suffix:
                    noms_entites.add(fichier.stem)

        return sorted(noms_entites)