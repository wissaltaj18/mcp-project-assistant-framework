"""
Resource review_checklist.md -- générée automatiquement depuis les
rapports déjà calculés (DevelopmentRulesReport + ArchitectureAnalysisReport).
Fournit une checklist actionnable pour toute code review sur ce projet.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReviewChecklistReport:
    """Critères de review déduits des faits détectés sur le projet."""

    test_framework: Optional[str] = None
    linter: Optional[str] = None
    ci_system: Optional[str] = None
    naming_convention: Optional[str] = None
    layer_folders_detected: List[str] = field(default_factory=list)
    detected_patterns: List[str] = field(default_factory=list)

    def to_markdown_fragment(self) -> str:
        lignes = [
            "# Review Checklist — Knowledge Base",
            "",
            "_Générée automatiquement à partir de l'analyse du projet. "
            "Modifier ce fichier pour adapter les critères à votre contexte._",
            "",
        ]

        lignes.append("## CHECKLIST_MANDATORY — Critères bloquants")
        lignes.append("_Toute PR ne respectant pas ces points est refusée._")
        lignes.append("")
        lignes.extend(f"- [ ] {item}" for item in self._construire_obligatoires())

        lignes.append("")
        lignes.append("## CHECKLIST_RECOMMENDED — Critères recommandés")
        lignes.append("_Non bloquants, mais à justifier si non respectés._")
        lignes.append("")
        lignes.extend(f"- [ ] {item}" for item in self._construire_recommandes())

        par_couche = self._construire_par_couche()
        if par_couche:
            lignes.append("")
            lignes.append("## CHECKLIST_ARCHITECTURE — Respect des couches détectées")
            lignes.append("")
            lignes.extend(f"- [ ] {item}" for item in par_couche)

        par_pattern = self._construire_par_pattern()
        if par_pattern:
            lignes.append("")
            lignes.append("## CHECKLIST_PATTERNS — Respect des patterns détectés")
            lignes.append("")
            lignes.extend(f"- [ ] {item}" for item in par_pattern)

        return "\n".join(lignes)

    def _construire_obligatoires(self) -> List[str]:
        items = [
            "Le code compile / s'exécute sans erreur.",
            "Aucun secret (token, mot de passe, clé API) n'est commité.",
            "Aucune dépendance introduite sans justification dans le PR.",
        ]
        if self.test_framework:
            items.append(
                f"Les tests {self.test_framework} passent tous au vert "
                f"(framework détecté : {self.test_framework})."
            )
        else:
            items.append(
                "Des tests sont ajoutés pour le nouveau code "
                "(aucun framework détecté -- en définir un)."
            )
        if self.naming_convention:
            convention = self.naming_convention.split(" ")[0]
            items.append(
                f"La convention de nommage {convention} est respectée "
                f"(détectée : {self.naming_convention})."
            )
        if self.ci_system:
            items.append(f"La CI ({self.ci_system}) passe au vert avant le merge.")
        return items

    def _construire_recommandes(self) -> List[str]:
        items = [
            "Les fonctions/méthodes font moins de 30 lignes.",
            "Les noms expriment l'intention, pas l'implémentation.",
            "Pas de code mort ou commenté inutilement.",
            "Les messages de commit sont clairs et au présent.",
        ]
        if self.linter:
            items.append(f"Le linter {self.linter} ne remonte aucun avertissement.")
        return items

    def _construire_par_couche(self) -> List[str]:
        items = []
        if "controller" in self.layer_folders_detected:
            items.append("Les Controllers ne contiennent pas de logique métier (couche Controller détectée).")
        if "service" in self.layer_folders_detected:
            items.append("La logique métier est bien dans les Services (couche Service détectée).")
        if "repository" in self.layer_folders_detected:
            items.append("Les accès base de données passent par les Repositories (couche Repository détectée).")
        if "entity" in self.layer_folders_detected:
            items.append("Les Entities ne contiennent pas de logique applicative (couche Entity détectée).")
        return items

    def _construire_par_pattern(self) -> List[str]:
        items = []
        if "cqrs" in self.detected_patterns:
            items.append("Les Commands ne retournent pas de données métier (pattern CQRS détecté).")
            items.append("Les Queries ne modifient pas l'état (pattern CQRS détecté).")
        if "repository" in self.detected_patterns:
            items.append("Aucune requête SQL/ORM en dehors des Repositories (pattern Repository détecté).")
        return items