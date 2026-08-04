"""
Résultat d'une analyse factuelle d'architecture (sans LLM) -- porte
lui-même la responsabilité de son rendu Markdown, pour être directement
consommé par le futur ResourceGeneratorService sans logique de
transformation supplémentaire.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ArchitectureAnalysisReport:
    """Faits détectés sur un Workspace -- déterministes, vérifiables, aucune interprétation."""

    languages: List[str] = field(default_factory=list)
    primary_framework: Optional[str] = None
    layer_folders: Dict[str, List[str]] = field(default_factory=dict)
    build_system: Optional[str] = None
    entry_point: Optional[str] = None
    main_dependencies: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)

    def to_markdown_fragment(self) -> str:
        """Rend ce rapport en un fragment Markdown, prêt à devenir une section de technical_architecture.md."""
        lignes = ["# Architecture technique (détection automatique)", ""]

        lignes.append("## Langages détectés")
        if self.languages:
            lignes.extend(f"- {langage}" for langage in self.languages)
        else:
            lignes.append("- Aucun langage détecté")

        lignes.append("")
        lignes.append("## Framework principal")
        lignes.append(f"- {self.primary_framework}" if self.primary_framework else "- Aucun framework détecté")

        lignes.append("")
        lignes.append("## Dossiers par couche détectés")
        if self.layer_folders:
            for couche in sorted(self.layer_folders.keys()):
                chemins = self.layer_folders[couche]
                lignes.append(f"### {couche.capitalize()}")
                lignes.extend(f"- {chemin}" for chemin in chemins)
        else:
            lignes.append("Aucun dossier de couche détecté.")

        lignes.append("")
        lignes.append("## Système de build / gestionnaire de dépendances")
        lignes.append(f"- {self.build_system}" if self.build_system else "Information non disponible.")

        lignes.append("")
        lignes.append("## Point d'entrée de l'application")
        lignes.append(f"- {self.entry_point}" if self.entry_point else "Information non disponible.")

        lignes.append("")
        lignes.append("## Dépendances principales détectées")
        if self.main_dependencies:
            lignes.extend(f"- {dep}" for dep in self.main_dependencies)
        else:
            lignes.append("Information non disponible.")

        lignes.append("")
        lignes.append("## Fichiers de configuration détectés")
        if self.config_files:
            lignes.extend(f"- {fichier}" for fichier in self.config_files)
        else:
            lignes.append("Aucun fichier de configuration détecté.")

        return "\n".join(lignes)