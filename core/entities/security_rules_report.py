"""
Resource security_rules.md -- générée automatiquement depuis
ArchitectureAnalysisReport + KnowledgeBaseRulesLoader.
Règles de sécurité : globales + spécifiques au framework détecté.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SecurityRulesReport:
    """Règles de sécurité déduites du framework et de l'architecture détectés."""

    primary_framework: Optional[str] = None
    global_rules: List[str] = field(default_factory=list)
    framework_rules: List[str] = field(default_factory=list)

    def to_markdown_fragment(self) -> str:
        lignes = [
            "# Règles de sécurité — Knowledge Base",
            "",
            "_Générée automatiquement à partir du framework détecté. "
            "Modifier ce fichier pour ajouter des règles spécifiques au projet._",
            "",
        ]

        lignes.append("## SECURITY_GLOBAL — Règles applicables à tout projet")
        lignes.append("_Ces règles s'appliquent indépendamment du framework ou du langage._")
        lignes.append("")
        if self.global_rules:
            lignes.extend(f"- {r}" for r in self.global_rules)
        else:
            lignes.append("- Information non disponible.")

        if self.framework_rules:
            lignes.append("")
            lignes.append(
                f"## SECURITY_FRAMEWORK — Règles spécifiques à {self.primary_framework or 'ce framework'}"
            )
            lignes.append(
                "_Ces règles sont déduites de la documentation de sécurité officielle du framework détecté._"
            )
            lignes.append("")
            lignes.extend(f"- {r}" for r in self.framework_rules)
        elif self.primary_framework:
            lignes.append("")
            lignes.append(f"## SECURITY_FRAMEWORK — {self.primary_framework}")
            lignes.append(
                f"Aucune règle de sécurité spécifique à `{self.primary_framework}` "
                "dans la Knowledge Base. Ajouter une entrée dans "
                "`services/knowledge_base_rules.json` sous la clé `security_rules`."
            )

        lignes.append("")
        lignes.append("---")
        lignes.append("")
        lignes.append("## CONSTRAINTS — Non négociables pour toute PR")
        lignes.append("- Aucun secret commité dans le dépôt Git (vérifier avec `git log --all`).")
        lignes.append("- Toute entrée utilisateur est validée côté serveur avant traitement.")
        lignes.append("- Toute vulnérabilité détectée est documentée dans le PR avant merge.")

        return "\n".join(lignes)