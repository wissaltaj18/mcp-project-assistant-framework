"""
Génère review_checklist.md depuis les rapports déjà calculés --
ne fait aucune analyse supplémentaire, compose uniquement
DevelopmentRulesReport + ArchitectureAnalysisReport.
"""

from core.entities.review_checklist_report import ReviewChecklistReport


class ReviewChecklistGeneratorService:
    """Compose un ReviewChecklistReport depuis les rapports déjà disponibles."""

    def generate(self, development_rules_report, architecture_report) -> ReviewChecklistReport:
        return ReviewChecklistReport(
            test_framework=development_rules_report.test_framework,
            linter=development_rules_report.linter,
            ci_system=development_rules_report.ci_system,
            naming_convention=development_rules_report.naming_convention,
            layer_folders_detected=list(architecture_report.layer_folders.keys()),
            detected_patterns=list(getattr(architecture_report, "detected_patterns", [])),
        )