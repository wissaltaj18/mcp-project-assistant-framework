"""
Analyse FACTUELLE d'un Workspace -- étendu au Sprint 19 avec la détection
de patterns architecturaux (MVC, Repository, CQRS, Clean Architecture,
Hexagonal, DDD) par analyse des noms de dossiers, et détection étendue
de frameworks (FastAPI, NestJS, ASP.NET Core, Angular, Vue).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.entities.architecture_analysis_report import ArchitectureAnalysisReport

EXTENSIONS_VERS_LANGAGE: Dict[str, str] = {
    ".py": "Python", ".php": "PHP", ".js": "JavaScript", ".ts": "TypeScript",
    ".java": "Java", ".cs": "C#", ".go": "Go", ".rb": "Ruby",
    ".rs": "Rust", ".cpp": "C++", ".kt": "Kotlin",
}

DOSSIERS_A_IGNORER = {
    "vendor", "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "target", "bin", "obj",
}

MOTIFS_PAR_COUCHE: Dict[str, List[str]] = {
    "controller": ["controller", "controllers"],
    "service": ["service", "services"],
    "entity": ["entity", "entities", "model", "models"],
    "repository": ["repository", "repositories"],
    "template": ["template", "templates"],
}

MANIFESTES_VERS_BUILD_SYSTEM = [
    ("composer.json", "Composer (PHP)"),
    ("package.json", "npm/yarn (Node.js)"),
    ("requirements.txt", "pip (Python)"),
    ("pyproject.toml", "pip/poetry (Python)"),
    ("pom.xml", "Maven (Java)"),
    ("build.gradle", "Gradle (Java)"),
    ("Cargo.toml", "Cargo (Rust)"),
    ("go.mod", "Go Modules"),
]

POINTS_ENTREE_CANDIDATS = [
    "public/index.php", "index.php", "manage.py", "app.py", "main.py",
    "Program.cs", "src/index.js", "src/index.ts", "src/main.js", "src/main.ts",
    "cmd/main.go", "main.go", "src/main.rs",
]

FICHIERS_CONFIG_CANDIDATS = [
    ".env.example", ".env.sample", "appsettings.json",
    "appsettings.Development.json", "settings.py", "config.py",
]
DOSSIERS_CONFIG_A_SCANNER = ["config"]
EXTENSIONS_CONFIG_DANS_DOSSIER = {".yaml", ".yml", ".json", ".ini", ".toml"}
MAX_DEPENDANCES_LISTEES = 15

_PATTERNS_ARCHITECTURAUX = {
    "mvc": {
        "required": [{"controller", "controllers"}, {"model", "models", "entity", "entities"}],
        "optional": [{"view", "views", "template", "templates"}],
    },
    "repository": {
        "required": [{"repository", "repositories"}],
        "optional": [],
    },
    "cqrs": {
        "required": [{"command", "commands"}, {"query", "queries"}],
        "optional": [{"handler", "handlers"}],
    },
    "clean_architecture": {
        "required": [{"domain"}, {"application"}, {"infrastructure"}],
        "optional": [{"presentation"}],
    },
    "hexagonal": {
        "required": [{"port", "ports"}, {"adapter", "adapters"}],
        "optional": [],
    },
    "ddd": {
        "required": [{"domain"}],
        "optional": [{"aggregate", "aggregates"}, {"valueobject", "valueobjects"}],
    },
}


class ArchitectureAnalyzerService:

    def analyze(self, repo_path: str) -> ArchitectureAnalysisReport:
        racine = Path(repo_path)
        if not racine.exists():
            return ArchitectureAnalysisReport()

        detected_patterns, partial_patterns = self._detecter_patterns_architecturaux(racine)

        return ArchitectureAnalysisReport(
            languages=self._detecter_langages(racine),
            primary_framework=self._detecter_framework(racine),
            layer_folders=self._detecter_dossiers_par_couche(racine),
            build_system=self._detecter_build_system(racine),
            entry_point=self._detecter_point_entree(racine),
            main_dependencies=self._detecter_dependances_principales(racine),
            config_files=self._detecter_fichiers_config(racine),
            detected_patterns=detected_patterns,
            partial_patterns=partial_patterns,
            architectural_violations=self._detecter_violations_architecturales(racine),
        )

    def _detecter_langages(self, racine: Path) -> list:
        extensions_trouvees = set()
        for fichier in racine.rglob("*"):
            if fichier.is_file() and fichier.suffix in EXTENSIONS_VERS_LANGAGE:
                extensions_trouvees.add(EXTENSIONS_VERS_LANGAGE[fichier.suffix])
        return sorted(extensions_trouvees)

    def _detecter_framework(self, racine: Path) -> Optional[str]:
        detecteurs = [
            self._detecter_framework_composer,
            self._detecter_framework_package_json,
            self._detecter_framework_requirements,
            self._detecter_framework_pom,
            self._detecter_framework_csproj,
        ]
        for detecteur in detecteurs:
            resultat = detecteur(racine)
            if resultat is not None:
                return resultat
        return None

    def _lire_json(self, chemin: Path) -> "dict | None":
        try:
            return json.loads(chemin.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            return None

    def _detecter_framework_composer(self, racine: Path) -> Optional[str]:
        chemin = racine / "composer.json"
        if not chemin.exists():
            return None
        donnees = self._lire_json(chemin)
        if donnees is None:
            return None
        dependances = {**donnees.get("require", {}), **donnees.get("require-dev", {})}
        if any(p.startswith("symfony/") for p in dependances):
            return "Symfony (PHP)"
        if any(p.startswith("laravel/") for p in dependances):
            return "Laravel (PHP)"
        return None

    def _detecter_framework_package_json(self, racine: Path) -> Optional[str]:
        chemin = racine / "package.json"
        if not chemin.exists():
            return None
        donnees = self._lire_json(chemin)
        if donnees is None:
            return None
        dependances = {**donnees.get("dependencies", {}), **donnees.get("devDependencies", {})}
        if "@nestjs/core" in dependances:
            return "NestJS (TypeScript)"
        if "react" in dependances:
            return "React (JavaScript/TypeScript)"
        if "@angular/core" in dependances:
            return "Angular (TypeScript)"
        if "vue" in dependances:
            return "Vue (JavaScript/TypeScript)"
        if "express" in dependances:
            return "Express (JavaScript/TypeScript)"
        return None

    def _detecter_framework_requirements(self, racine: Path) -> Optional[str]:
        chemin = racine / "requirements.txt"
        if not chemin.exists():
            return None
        try:
            contenu = chemin.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            return None
        if "fastapi" in contenu:
            return "FastAPI (Python)"
        if "django" in contenu:
            return "Django (Python)"
        if "flask" in contenu:
            return "Flask (Python)"
        return None

    def _detecter_framework_pom(self, racine: Path) -> Optional[str]:
        chemin = racine / "pom.xml"
        if not chemin.exists():
            return None
        try:
            contenu = chemin.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        if "spring-boot" in contenu:
            return "Spring Boot (Java)"
        return None

    def _detecter_framework_csproj(self, racine: Path) -> Optional[str]:
        fichiers_csproj = list(racine.glob("**/*.csproj"))
        if not fichiers_csproj:
            return None
        try:
            contenu = fichiers_csproj[0].read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        if "Microsoft.AspNetCore" in contenu:
            return "ASP.NET Core (C#)"
        return None

    def _detecter_dossiers_par_couche(self, racine: Path) -> Dict[str, List[str]]:
        resultat: Dict[str, List[str]] = {}
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(partie in DOSSIERS_A_IGNORER for partie in dossier.parts):
                continue
            nom_minuscule = dossier.name.lower()
            for couche, motifs in MOTIFS_PAR_COUCHE.items():
                if nom_minuscule in motifs:
                    chemin_relatif = str(dossier.relative_to(racine))
                    resultat.setdefault(couche, []).append(chemin_relatif)
        for couche in resultat:
            resultat[couche] = sorted(resultat[couche])
        return resultat

    def _detecter_build_system(self, racine: Path) -> Optional[str]:
        for nom_fichier, nom_build in MANIFESTES_VERS_BUILD_SYSTEM:
            if (racine / nom_fichier).exists():
                return nom_build
        if list(racine.glob("**/*.csproj")):
            return "MSBuild (.NET)"
        return None

    def _detecter_point_entree(self, racine: Path) -> Optional[str]:
        for candidat in POINTS_ENTREE_CANDIDATS:
            if (racine / candidat).exists():
                return candidat
        return None

    def _detecter_dependances_principales(self, racine: Path) -> List[str]:
        chemin_composer = racine / "composer.json"
        if chemin_composer.exists():
            donnees = self._lire_json(chemin_composer)
            if donnees:
                return sorted(donnees.get("require", {}).keys())[:MAX_DEPENDANCES_LISTEES]
        chemin_package = racine / "package.json"
        if chemin_package.exists():
            donnees = self._lire_json(chemin_package)
            if donnees:
                return sorted(donnees.get("dependencies", {}).keys())[:MAX_DEPENDANCES_LISTEES]
        return []

    def _detecter_fichiers_config(self, racine: Path) -> List[str]:
        trouves = []
        for candidat in FICHIERS_CONFIG_CANDIDATS:
            if (racine / candidat).exists():
                trouves.append(candidat)
        for nom_dossier in DOSSIERS_CONFIG_A_SCANNER:
            dossier = racine / nom_dossier
            if dossier.is_dir():
                for fichier in dossier.iterdir():
                    if fichier.is_file() and fichier.suffix in EXTENSIONS_CONFIG_DANS_DOSSIER:
                        trouves.append(str(fichier.relative_to(racine)))
        return sorted(trouves)
    def _detecter_violations_architecturales(self, racine: Path) -> List[str]:
        """
        Détecte les violations Controller → Repository (import direct).
        Cherche dans les fichiers Controller des `use` statements qui
        importent depuis un namespace Repository. Retourne une liste
        de violations concrètes avec le fichier source.
        """
        violations = []
        dossiers_controller = []
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(p in DOSSIERS_A_IGNORER for p in dossier.parts):
                continue
            if dossier.name.lower() in ("controller", "controllers"):
                dossiers_controller.append(dossier)

        for dossier_ctrl in dossiers_controller:
            for fichier in dossier_ctrl.rglob("*"):
                if not fichier.is_file() or fichier.suffix not in (".php", ".py", ".ts", ".java", ".cs"):
                    continue
                try:
                    contenu = fichier.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                chemin_relatif = str(fichier.relative_to(racine)).replace("\\", "/")
                if fichier.suffix == ".php":
                    for ligne in contenu.splitlines():
                        ligne_strip = ligne.strip()
                        if (ligne_strip.startswith("use ")
                                and "Repository" in ligne_strip
                                and not ligne_strip.startswith("//")):
                            import_name = ligne_strip.replace("use ", "").rstrip(";").strip()
                            violations.append(
                                f"`{chemin_relatif}` importe directement `{import_name}` "
                                f"-- passer par un Service au lieu d'accéder au Repository directement."
                            )
                elif fichier.suffix == ".java":
                    for ligne in contenu.splitlines():
                        ligne_strip = ligne.strip()
                        if ligne_strip.startswith("import ") and ".repository." in ligne_strip.lower():
                            import_name = ligne_strip.replace("import ", "").rstrip(";").strip()
                            violations.append(
                                f"`{chemin_relatif}` importe directement `{import_name}` "
                                f"-- passer par un @Service au lieu d'accéder au Repository directement."
                            )
        return violations

    def _detecter_patterns_architecturaux(self, racine: Path) -> Tuple[List[str], List[str]]:
        noms_dossiers = set()
        for dossier in racine.rglob("*"):
            if not dossier.is_dir():
                continue
            if any(partie in DOSSIERS_A_IGNORER for partie in dossier.parts):
                continue
            noms_dossiers.add(dossier.name.lower())

        confirmes = []
        partiels = []

        for nom_pattern, definition in _PATTERNS_ARCHITECTURAUX.items():
            groupes_requis = definition["required"]
            groupes_trouves = sum(
                1 for groupe in groupes_requis
                if any(nom in noms_dossiers for nom in groupe)
            )
            if groupes_trouves == len(groupes_requis):
                confirmes.append(nom_pattern)
            elif groupes_trouves > 0:
                partiels.append(nom_pattern)

        return sorted(confirmes), sorted(partiels)