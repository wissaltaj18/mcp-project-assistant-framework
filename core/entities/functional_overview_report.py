"""
Résultat d'une analyse fonctionnelle FACTUELLE (aucun LLM) d'un
Workspace -- ne fait que CITER ce qui existe déjà dans le dépôt
(description de manifeste, extrait de README, dossiers présents, routes,
entités), jamais de résumé synthétisé. Toute information absente est
indiquée honnêtement comme telle, jamais inventée.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FunctionalOverviewReport:
    """Faits fonctionnels détectés -- cités tels quels depuis le dépôt, jamais reformulés."""

    description: Optional[str] = None
    readme_excerpt: Optional[str] = None
    top_level_folders: List[str] = field(default_factory=list)
    pattern_matched_folders: List[str] = field(default_factory=list)
    detected_routes: Optional[str] = None
    detected_entities: List[str] = field(default_factory=list)

    def to_markdown_fragment(self) -> str:
        lignes = ["# Vue fonctionnelle (détection automatique)", ""]

        lignes.append("## Description")
        lignes.append(self.description if self.description else "Information non disponible.")

        lignes.append("")
        lignes.append("## Extrait du README")
        lignes.append(self.readme_excerpt if self.readme_excerpt else "Aucun README trouvé.")

        lignes.append("")
        lignes.append("## Dossiers principaux du dépôt")
        if self.top_level_folders:
            lignes.extend(f"- {dossier}" for dossier in self.top_level_folders)
        else:
            lignes.append("Information non disponible.")

        lignes.append("")
        lignes.append("## Dossiers correspondant à des motifs courants (controller/service/route...)")
        if self.pattern_matched_folders:
            lignes.extend(f"- {dossier}" for dossier in self.pattern_matched_folders)
        else:
            lignes.append("Aucun dossier de ce type détecté.")

        lignes.append("")
        lignes.append("## Points d'entrée utilisateur (routes)")
        lignes.append(self.detected_routes if self.detected_routes else "Aucun fichier de routes trouvé.")

        lignes.append("")
        lignes.append("## Entités / modèles détectés")
        if self.detected_entities:
            lignes.extend(f"- {entite}" for entite in self.detected_entities)
        else:
            lignes.append("Information non disponible.")

        return "\n".join(lignes)