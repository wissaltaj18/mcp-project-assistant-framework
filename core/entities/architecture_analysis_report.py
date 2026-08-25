"""
Résultat d'une analyse factuelle d'architecture (sans LLM).

Sprint 19 (révisé) : to_markdown_fragment() est un moteur générique --
il délègue au KnowledgeBaseRulesLoader pour toutes les règles par
framework, langage et pattern. Ajouter un nouveau framework = éditer
knowledge_base_rules.json, pas ce fichier.

Nouveaux champs :
  detected_patterns  : patterns architecturaux confirmés
  partial_patterns   : patterns détectés partiellement
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from services.knowledge_base_rules_loader import KnowledgeBaseRulesLoader

_loader = KnowledgeBaseRulesLoader()


@dataclass
class ArchitectureAnalysisReport:
    """Faits détectés + Best Practices déduites via le moteur générique."""

    languages: List[str] = field(default_factory=list)
    primary_framework: Optional[str] = None
    layer_folders: Dict[str, List[str]] = field(default_factory=dict)
    build_system: Optional[str] = None
    entry_point: Optional[str] = None
    main_dependencies: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    detected_patterns: List[str] = field(default_factory=list)
    partial_patterns: List[str] = field(default_factory=list)
    architectural_violations: List[str] = field(default_factory=list)

    def to_markdown_fragment(self) -> str:
        lignes = ["# Architecture technique — Knowledge Base", ""]

        # ── FACTS ──────────────────────────────────────────────────────────
        lignes.append("## FACTS — Éléments détectés automatiquement")
        lignes.append("")

        lignes.append("### Langages")
        if self.languages:
            lignes.extend(f"- {lang}" for lang in self.languages)
        else:
            lignes.append("- Aucun langage détecté")

        lignes.append("")
        lignes.append("### Framework principal")
        if self.primary_framework:
            known = "✓ connu" if _loader.framework_is_known(self.primary_framework) else "~ non référencé dans la Knowledge Base"
            lignes.append(f"- {self.primary_framework} ({known})")
        else:
            lignes.append("- Non détecté")

        lignes.append("")
        lignes.append("### Système de build")
        lignes.append(f"- {self.build_system}" if self.build_system else "- Non détecté")

        lignes.append("")
        lignes.append("### Point d'entrée")
        lignes.append(f"- `{self.entry_point}`" if self.entry_point else "- Non détecté")

        lignes.append("")
        lignes.append("### Couches architecturales détectées")
        if self.layer_folders:
            for couche, chemins in sorted(self.layer_folders.items()):
                lignes.append(f"- **{couche.capitalize()}** : {', '.join(f'`{c}`' for c in chemins)}")
        else:
            lignes.append("- Aucune couche détectée")

        lignes.append("")
        lignes.append("### Patterns architecturaux")
        if self.detected_patterns:
            for p in self.detected_patterns:
                desc = _loader.get_pattern_description(p)
                lignes.append(f"- **{p.upper()}** — {desc}" if desc else f"- **{p.upper()}**")
        else:
            lignes.append("- Aucun pattern architectural confirmé détecté")
        if self.partial_patterns:
            lignes.append("")
            lignes.append("  _Implémentation partielle détectée :_")
            lignes.extend(f"  - {p} (partiel)" for p in self.partial_patterns)

        lignes.append("")
        lignes.append("### Dépendances principales")
        if self.main_dependencies:
            lignes.extend(f"- `{dep}`" for dep in self.main_dependencies)
        else:
            lignes.append("- Aucune")

        lignes.append("")
        lignes.append("### Fichiers de configuration")
        if self.config_files:
            lignes.extend(f"- `{f}`" for f in self.config_files)
        else:
            lignes.append("- Aucun")

        # ── BEST PRACTICES PAR LANGAGE ──────────────────────────────────────
        bp_langages = self._construire_bp_langages()
        if bp_langages:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## BEST PRACTICES — Par langage")
            for lang, bps in bp_langages.items():
                lignes.append(f"### {lang}")
                lignes.extend(f"- {bp}" for bp in bps)

        # ── BEST PRACTICES PAR FRAMEWORK ───────────────────────────────────
        bp_framework = self._construire_bp_framework()
        if bp_framework:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append(f"## BEST PRACTICES — {self.primary_framework}")
            lignes.append(
                "_Règles déduites de la documentation officielle du framework, "
                "appliquées uniquement aux couches réellement présentes dans ce dépôt._"
            )
            for couche, bps in bp_framework.items():
                lignes.append(f"### {couche.capitalize()}")
                lignes.extend(f"- {bp}" for bp in bps)

        # ── BEST PRACTICES PAR PATTERN ─────────────────────────────────────
        bp_patterns = self._construire_bp_patterns()
        if bp_patterns:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## BEST PRACTICES — Patterns architecturaux détectés")
            for pattern, bps in bp_patterns.items():
                lignes.append(f"### {pattern.upper()}")
                lignes.extend(f"- {bp}" for bp in bps)

        # ── ANTI-PATTERNS ──────────────────────────────────────────────────
        anti_patterns = self._construire_anti_patterns()
        if anti_patterns:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## ANTI-PATTERNS — À éviter dans ce projet")
            lignes.extend(f"- {ap}" for ap in anti_patterns)

        # ── CONSTRAINTS ────────────────────────────────────────────────────
        constraints = self._construire_constraints()
        if constraints:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## CONSTRAINTS — Règles non négociables")
            lignes.extend(f"- {c}" for c in constraints)

        # ── OPEN QUESTIONS ─────────────────────────────────────────────────
        if self.primary_framework and not _loader.framework_is_known(self.primary_framework):
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## OPEN QUESTIONS")
            lignes.append(
                f"- Le framework `{self.primary_framework}` n'est pas encore référencé "
                "dans la Knowledge Base. Ajouter ses règles dans "
                "`services/knowledge_base_rules.json` pour enrichir les futures analyses."
            )
        # ── VIOLATIONS DÉTECTÉES ───────────────────────────────────────────
        if self.architectural_violations:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## VIOLATIONS DÉTECTÉES — À corriger en priorité")
            lignes.append(
                "_Violations architecturales détectées statiquement dans le code existant._"
            )
            for v in self.architectural_violations:
                lignes.append(f"- {v}")


        return "\n".join(lignes)

    def _construire_bp_langages(self) -> Dict[str, List[str]]:
        resultat = {}
        for lang in self.languages:
            bps = _loader.get_language_best_practices(lang)
            if bps:
                resultat[lang] = bps
        return resultat

    def _construire_bp_framework(self) -> Dict[str, List[str]]:
        if not self.primary_framework:
            return {}
        return _loader.get_framework_layer_best_practices_for_detected_layers(
            self.primary_framework, list(self.layer_folders.keys())
        )

    def _construire_bp_patterns(self) -> Dict[str, List[str]]:
        resultat = {}
        for pattern in self.detected_patterns:
            bps = _loader.get_pattern_best_practices(pattern)
            if bps:
                resultat[pattern] = bps
        return resultat

    def _construire_anti_patterns(self) -> List[str]:
        tous = []
        if self.primary_framework:
            tous.extend(_loader.get_all_framework_anti_patterns(self.primary_framework))
        for pattern in self.detected_patterns:
            tous.extend(_loader.get_pattern_anti_patterns(pattern))
        vus: set = set()
        resultat = []
        for ap in tous:
            if ap not in vus:
                vus.add(ap)
                resultat.append(ap)
        return resultat

    def _construire_constraints(self) -> List[str]:
        constraints = []
        if self.layer_folders:
            couches = sorted(self.layer_folders.keys())
            couches_str = " → ".join(c.capitalize() for c in couches)
            constraints.append(
                f"Respecter l'ordre des couches détectées : {couches_str}. "
                "Un appel ne doit jamais sauter une couche."
            )
        if self.entry_point:
            constraints.append(
                f"Le point d'entrée `{self.entry_point}` ne doit pas contenir "
                "de logique applicative -- il orchestre uniquement le démarrage."
            )
        if self.main_dependencies:
            constraints.append(
                "Avant d'ajouter une nouvelle dépendance, vérifier qu'elle "
                "n'est pas déjà couverte par les dépendances existantes listées ci-dessus."
            )
        if "cqrs" in self.partial_patterns:
            constraints.append(
                "CQRS partiellement implémenté : s'assurer que la séparation "
                "Commands/Queries est complète avant d'ajouter de nouvelles opérations."
            )
        return constraints