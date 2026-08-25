"""
Analyse fonctionnelle FACTUELLE (deterministe, aucun LLM).

Sprint 24 : _detecter_relations_doctrine() + _grouper_routes_par_domaine()
Sprint 25 : _detecter_correspondances_controller_template() depuis render()
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from core.entities.functional_overview_report import FunctionalOverviewReport

DOSSIERS_A_IGNORER = {
    "vendor", "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "target", "bin", "obj",
}

MOTIFS_DOSSIERS_COURANTS = [
    "controller", "controllers", "service", "services",
    "route", "routes", "entity", "entities", "model", "models",
    "template", "templates",
]

FICHIERS_ROUTES_CANDIDATS = [
    "routes/web.php", "routes/api.php", "urls.py", "src/routes.js",
    "src/routes.ts", "config/routes.yaml",
]

TAILLE_MAX_EXTRAIT = 500

_REGEX_RELATION_ATTRIBUT = re.compile(
    r'#\[ORM\\(OneToMany|ManyToOne|ManyToMany|OneToOne)\s*\(([^)]*)\)',
    re.IGNORECASE,
)
_REGEX_RELATION_ANNOTATION = re.compile(
    r'@ORM\\(OneToMany|ManyToOne|ManyToMany|OneToOne)\s*\(([^)]*)\)',
    re.IGNORECASE,
)
_REGEX_TARGET_ENTITY = re.compile(
    r'targetEntity\s*[=:]\s*["\']?(\w+)(?:::class)?["\']?',
    re.IGNORECASE,
)
_REGEX_MAPPED_BY = re.compile(r'mappedBy\s*[=:]\s*["\']?(\w+)["\']?', re.IGNORECASE)
_REGEX_INVERSED_BY = re.compile(r'inversedBy\s*[=:]\s*["\']?(\w+)["\']?', re.IGNORECASE)
_REGEX_ROUTE_ATTRIBUT = re.compile(
    r'#\[Route\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_REGEX_RENDER = re.compile(
    r'return\s+\$this->render\s*\(\s*["\']([^"\']+\.twig)["\']',
    re.IGNORECASE,
)


class FunctionalOverviewAnalyzerService:

    def __init__(self, architecture_analyzer=None):
        self._architecture_analyzer = architecture_analyzer

    def analyze(self, repo_path: str) -> FunctionalOverviewReport:
        racine = Path(repo_path)
        if not racine.exists():
            return FunctionalOverviewReport()

        detected_entities = self._lister_entites(racine)
        entity_relations = self._detecter_relations_doctrine(racine)
        routes_par_domaine = self._grouper_routes_par_domaine(racine, detected_entities)
        controller_template_map = self._detecter_correspondances_controller_template(racine)

        return FunctionalOverviewReport(
            description=self._lire_description_manifeste(racine),
            readme_excerpt=self._lire_extrait_readme(racine),
            top_level_folders=self._lister_dossiers_principaux(racine),
            pattern_matched_folders=self._detecter_dossiers_par_motif(racine),
            detected_routes=self._lire_fichier_routes(racine),
            detected_entities=detected_entities,
            entity_relations=entity_relations,
            routes_par_domaine=routes_par_domaine,
            controller_template_map=controller_template_map,
        )

    def _lire_json(self, chemin: Path) -> "dict | None":
        try:
            return json.loads(chemin.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            return None

    def _lire_description_manifeste(self, racine: Path) -> Optional[str]:
        for nom in ("composer.json", "package.json"):
            chemin = racine / nom
            if not chemin.exists():
                continue
            donnees = self._lire_json(chemin)
            if donnees and donnees.get("description"):
                return str(donnees["description"]).strip()
        return None

    def _lire_extrait_readme(self, racine: Path) -> Optional[str]:
        for nom in ("README.md", "readme.md", "Readme.md", "README.MD"):
            chemin = racine / nom
            if chemin.exists():
                try:
                    contenu = chemin.read_text(encoding="utf-8", errors="ignore").strip()
                except OSError:
                    continue
                if contenu:
                    return contenu[:TAILLE_MAX_EXTRAIT]
        return None

    def _lister_dossiers_principaux(self, racine: Path) -> List[str]:
        try:
            return sorted(
                f.name for f in racine.iterdir()
                if f.is_dir() and f.name not in DOSSIERS_A_IGNORER
                and not f.name.startswith(".")
            )
        except OSError:
            return []

    def _detecter_dossiers_par_motif(self, racine: Path) -> List[str]:
        trouves = []
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(p in DOSSIERS_A_IGNORER for p in dossier.parts):
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
        if self._architecture_analyzer:
            rapport = self._architecture_analyzer.analyze(str(racine))
            dossiers_entites = rapport.layer_folders.get("entity", [])
            noms = set()
            for chemin_rel in dossiers_entites:
                dossier = racine / chemin_rel
                if dossier.is_dir():
                    for f in dossier.iterdir():
                        if f.is_file() and f.suffix:
                            noms.add(f.stem)
            return sorted(noms)
        noms = set()
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(p in DOSSIERS_A_IGNORER for p in dossier.parts):
                continue
            if dossier.name.lower() in ("entity", "entities", "model", "models"):
                for f in dossier.iterdir():
                    if f.is_file() and f.suffix:
                        noms.add(f.stem)
        return sorted(noms)

    def _detecter_correspondances_controller_template(self, racine: Path) -> Dict[str, List[str]]:
        """
        Détecte les correspondances Controller -> Template en lisant
        les appels return $this->render(...) dans les Controllers PHP.
        Retourne {NomController: [liste de templates rendus]}.
        """
        correspondances: Dict[str, List[str]] = {}

        dossiers_controller = []
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(p in DOSSIERS_A_IGNORER for p in dossier.parts):
                continue
            if dossier.name.lower() in ("controller", "controllers"):
                dossiers_controller.append(dossier)

        for dossier in dossiers_controller:
            for fichier in dossier.glob("*.php"):
                try:
                    contenu = fichier.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                templates = _REGEX_RENDER.findall(contenu)
                if templates:
                    vus: set = set()
                    templates_uniques = []
                    for t in templates:
                        if t not in vus:
                            vus.add(t)
                            templates_uniques.append(t)
                    correspondances[fichier.stem] = templates_uniques

        return correspondances

    def _detecter_relations_doctrine(self, racine: Path) -> Dict[str, List[str]]:
        """
        Détecte les relations Doctrine par analyse textuelle des fichiers Entity.
        """
        relations: Dict[str, List[str]] = {}

        dossiers_entity = []
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(p in DOSSIERS_A_IGNORER for p in dossier.parts):
                continue
            if dossier.name.lower() in ("entity", "entities"):
                dossiers_entity.append(dossier)

        for dossier in dossiers_entity:
            for fichier in dossier.glob("*.php"):
                try:
                    contenu = fichier.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                nom_entite = fichier.stem
                rels_entite = []

                for regex in (_REGEX_RELATION_ATTRIBUT, _REGEX_RELATION_ANNOTATION):
                    for match in regex.finditer(contenu):
                        type_relation = match.group(1)
                        params = match.group(2)

                        target = _REGEX_TARGET_ENTITY.search(params)
                        target_nom = target.group(1) if target else "?"

                        mapped = _REGEX_MAPPED_BY.search(params)
                        inversed = _REGEX_INVERSED_BY.search(params)

                        detail = ""
                        if mapped:
                            detail = f", mappedBy={mapped.group(1)}"
                        elif inversed:
                            detail = f", inversedBy={inversed.group(1)}"

                        rels_entite.append(
                            f"{type_relation} -> {target_nom}{detail}"
                        )

                if rels_entite:
                    relations[nom_entite] = rels_entite

        return relations

    def _grouper_routes_par_domaine(
        self, racine: Path, entites_detectees: List[str]
    ) -> Dict[str, List[str]]:
        """
        Groupe les routes par domaine métier.
        Priorité : 1. Nom Controller  2. Préfixe chemin  3. Autres
        """
        entites_index = {e.lower(): e for e in entites_detectees}
        routes_par_domaine: Dict[str, List[str]] = {}

        dossiers_controller = []
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(p in DOSSIERS_A_IGNORER for p in dossier.parts):
                continue
            if dossier.name.lower() in ("controller", "controllers"):
                dossiers_controller.append(dossier)

        for dossier in dossiers_controller:
            for fichier in dossier.glob("*.php"):
                try:
                    contenu = fichier.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                nom_fichier = fichier.stem
                domaine = None
                for entite_lower, entite_canon in entites_index.items():
                    if nom_fichier.lower().startswith(entite_lower):
                        domaine = entite_canon
                        break

                routes_trouvees = _REGEX_ROUTE_ATTRIBUT.findall(contenu)

                for route in routes_trouvees:
                    domaine_route = domaine
                    if domaine_route is None:
                        segments = [s for s in route.split("/") if s and "{" not in s]
                        if segments:
                            premier = segments[0].lower()
                            domaine_route = entites_index.get(premier, "Autres")
                        else:
                            domaine_route = "Autres"

                    routes_par_domaine.setdefault(domaine_route, [])
                    if route not in routes_par_domaine[domaine_route]:
                        routes_par_domaine[domaine_route].append(route)

        for domaine in routes_par_domaine:
            routes_par_domaine[domaine] = sorted(routes_par_domaine[domaine])

        return routes_par_domaine