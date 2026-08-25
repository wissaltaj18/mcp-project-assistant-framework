"""
Resultat d'une analyse fonctionnelle FACTUELLE (aucun LLM).

Sprint 24 : entity_relations + routes_par_domaine
Sprint 25 : controller_template_map (correspondance Controller -> Template)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FunctionalOverviewReport:
    description: Optional[str] = None
    readme_excerpt: Optional[str] = None
    top_level_folders: List[str] = field(default_factory=list)
    pattern_matched_folders: List[str] = field(default_factory=list)
    detected_routes: Optional[str] = None
    detected_entities: List[str] = field(default_factory=list)
    entity_relations: Dict[str, List[str]] = field(default_factory=dict)
    routes_par_domaine: Dict[str, List[str]] = field(default_factory=dict)
    controller_template_map: Dict[str, List[str]] = field(default_factory=dict)

    def to_markdown_fragment(self) -> str:
        lignes = ["# Vue fonctionnelle — Knowledge Base", ""]

        lignes.append("## FACTS — Contexte métier détecté automatiquement")
        lignes.append("")
        lignes.append("### Description du projet")
        lignes.append(self.description if self.description else "Information non disponible.")
        lignes.append("")
        lignes.append("### Extrait du README")
        lignes.append(self.readme_excerpt if self.readme_excerpt else "Aucun README trouvé.")
        lignes.append("")
        lignes.append("### Structure principale du dépôt")
        if self.top_level_folders:
            lignes.extend(f"- `{d}`" for d in self.top_level_folders)
        else:
            lignes.append("Information non disponible.")

        if self.detected_entities:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## VOCABULAIRE MÉTIER — Entités détectées")
            lignes.append(
                "_Ces entités constituent le vocabulaire officiel du projet. "
                "Utiliser EXACTEMENT ces noms dans tout nouveau code._"
            )
            for entite in self.detected_entities:
                lignes.append(f"- **{entite}**")
            lignes.append("")
            lignes.append(
                "> **CONSTRAINT** : Avant de créer une nouvelle entité, "
                "vérifier qu'elle ne correspond pas à l'une des entités existantes."
            )

        if self.entity_relations:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## RELATIONS ENTRE ENTITÉS — Modèle de données")
            lignes.append(
                "_Relations Doctrine détectées automatiquement. "
                "Respecter ces associations avant toute modification du modèle._"
            )
            for entite, relations in sorted(self.entity_relations.items()):
                lignes.append(f"### {entite}")
                lignes.extend(f"- {rel}" for rel in relations)
            lignes.append("")
            lignes.append(
                "> **CONSTRAINT** : Toute modification d'une relation Doctrine "
                "nécessite une migration de base de données."
            )

        if self.routes_par_domaine:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## ROUTES PAR DOMAINE — Points d'entrée utilisateur")
            lignes.append(
                "_Routes groupées par domaine métier. "
                "Vérifier l'existant avant d'ajouter une nouvelle route._"
            )
            for domaine, routes in sorted(self.routes_par_domaine.items()):
                lignes.append(f"### {domaine}")
                lignes.extend(f"- `{route}`" for route in routes)
            lignes.append("")
            lignes.append(
                "> **CONSTRAINT** : Ne pas créer de doublon fonctionnel "
                "avec les routes existantes ci-dessus."
            )
        elif self.detected_routes:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## POINTS D'ENTRÉE EXISTANTS — Routes détectées")
            lignes.append("")
            lignes.append("```")
            lignes.append(self.detected_routes)
            lignes.append("```")

        if self.controller_template_map:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## CORRESPONDANCE CONTROLLER — TEMPLATE")
            lignes.append(
                "_Correspondances détectées depuis les appels render() dans les Controllers. "
                "Identifier le template cible ici avant toute modification de page._"
            )
            for controller, templates in sorted(self.controller_template_map.items()):
                lignes.append(f"### {controller}")
                lignes.extend(f"- `{tpl}`" for tpl in templates)
            lignes.append("")
            lignes.append(
                "> **CONSTRAINT** : Pour modifier une page, identifier d'abord "
                "le template dans cette section plutôt que de parcourir l'arborescence."
            )

        if self.pattern_matched_folders:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## DOSSIERS FONCTIONNELS DÉTECTÉS")
            lignes.extend(f"- `{d}`" for d in self.pattern_matched_folders)

        lignes.append("")
        lignes.append("---")
        lignes.append("")
        lignes.append("## PREFERENCES — Cohérence fonctionnelle")
        lignes.append(
            "- Respecter le vocabulaire métier détecté ci-dessus dans les noms "
            "de variables, méthodes, classes et messages de commit."
        )
        if self.detected_entities:
            noms = ", ".join(self.detected_entities[:5])
            suite = "..." if len(self.detected_entities) > 5 else ""
            lignes.append(
                f"- Les entités ({noms}{suite}) doivent avoir une cohérence "
                "entre elles -- vérifier les relations avant toute création."
            )

        return "\n".join(lignes)