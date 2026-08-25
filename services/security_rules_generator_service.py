"""
Génère security_rules.md depuis ArchitectureAnalysisReport +
KnowledgeBaseRulesLoader -- ne fait aucune analyse supplémentaire.
"""

from core.entities.security_rules_report import SecurityRulesReport
from services.knowledge_base_rules_loader import KnowledgeBaseRulesLoader

_loader = KnowledgeBaseRulesLoader()


class SecurityRulesGeneratorService:
    """Compose un SecurityRulesReport depuis le rapport d'architecture et le loader."""

    def __init__(self, loader: KnowledgeBaseRulesLoader = None):
        self._loader = loader or _loader

    def generate(self, architecture_report) -> SecurityRulesReport:
        framework = architecture_report.primary_framework
        all_rules = self._loader.get_security_rules(framework)
        global_rules = self._loader.get_security_rules(None)
        framework_rules = [r for r in all_rules if r not in global_rules]
        return SecurityRulesReport(
            primary_framework=framework,
            global_rules=global_rules,
            framework_rules=framework_rules,
        )