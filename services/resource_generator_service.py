"""
Génère les Resources d'un Workspace. generate_all() est le point
d'entrée unique -- produit les 3 Resources complètes (technique,
fonctionnelle, règles de développement), toutes générées de façon
déterministe (aucun LLM).
"""

from typing import Dict, Optional

from core.ports.resource_writer_port import ResourceWriterPort
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.development_rules_analyzer_service import DevelopmentRulesAnalyzerService
from services.functional_overview_analyzer_service import FunctionalOverviewAnalyzerService

from services.review_checklist_generator_service import ReviewChecklistGeneratorService
from services.security_rules_generator_service import SecurityRulesGeneratorService
from services.template_resource_service import TemplateResourceService

NOM_FICHIER_TECHNICAL = "technical_architecture.md"
NOM_FICHIER_FUNCTIONAL = "functional_overview.md"
NOM_FICHIER_DEVELOPMENT_RULES = "development_rules.md"


class ResourceGeneratorService:
    """Cas d'usage : générer et écrire les Resources d'un Workspace depuis son analyse."""

    def __init__(
        self,
        architecture_analyzer: ArchitectureAnalyzerService,
        resource_writer: ResourceWriterPort,
        functional_overview_analyzer: Optional[FunctionalOverviewAnalyzerService] = None,
        development_rules_analyzer: Optional[DevelopmentRulesAnalyzerService] = None,
    ):
        self._analyzer = architecture_analyzer
        self._writer = resource_writer
        self._functional_analyzer = functional_overview_analyzer or FunctionalOverviewAnalyzerService(architecture_analyzer)
        self._development_rules_analyzer = development_rules_analyzer or DevelopmentRulesAnalyzerService(architecture_analyzer)
        self._review_checklist_generator = ReviewChecklistGeneratorService()
        self._security_rules_generator = SecurityRulesGeneratorService()
        self._template_resource_service = TemplateResourceService()

    def generate_all(self, repo_path: str, resources_dir: str) -> Dict[str, str]:
        """Point d'entrée unique : génère les 5 Resources automatiques
        et crée les 2 templates manuels si absents."""

        # ── 1. Analyse commune (évite de rejouer l'analyse 3 fois) ──────────
        rapport_arch = self._analyzer.analyze(repo_path)
        rapport_dev = self._development_rules_analyzer.analyze(repo_path)

        # ── 2. Resources automatiques ────────────────────────────────────────
        contenu_tech = rapport_arch.to_markdown_fragment()
        self._writer.write(resources_dir, NOM_FICHIER_TECHNICAL, contenu_tech)

        rapport_func = self._functional_analyzer.analyze(repo_path)
        contenu_func = rapport_func.to_markdown_fragment()
        self._writer.write(resources_dir, NOM_FICHIER_FUNCTIONAL, contenu_func)

        contenu_dev = rapport_dev.to_markdown_fragment()
        self._writer.write(resources_dir, NOM_FICHIER_DEVELOPMENT_RULES, contenu_dev)

        rapport_checklist = self._review_checklist_generator.generate(rapport_dev, rapport_arch)
        contenu_checklist = rapport_checklist.to_markdown_fragment()
        self._writer.write(resources_dir, "review_checklist.md", contenu_checklist)

        rapport_secu = self._security_rules_generator.generate(rapport_arch)
        contenu_secu = rapport_secu.to_markdown_fragment()
        self._writer.write(resources_dir, "security_rules.md", contenu_secu)

        # ── 3. Templates manuels (créés une seule fois, jamais écrasés) ──────
        self._template_resource_service.create_if_absent(resources_dir)

        return {
            NOM_FICHIER_TECHNICAL: contenu_tech,
            NOM_FICHIER_FUNCTIONAL: contenu_func,
            NOM_FICHIER_DEVELOPMENT_RULES: contenu_dev,
            "review_checklist.md": contenu_checklist,
            "security_rules.md": contenu_secu,
        }

    def generate_technical_architecture(self, repo_path: str, resources_dir: str) -> str:
        rapport = self._analyzer.analyze(repo_path)
        contenu = rapport.to_markdown_fragment()
        self._writer.write(resources_dir, NOM_FICHIER_TECHNICAL, contenu)
        return contenu

    def generate_functional_overview(self, repo_path: str, resources_dir: str) -> str:
        rapport = self._functional_analyzer.analyze(repo_path)
        contenu = rapport.to_markdown_fragment()
        self._writer.write(resources_dir, NOM_FICHIER_FUNCTIONAL, contenu)
        return contenu

    def generate_development_rules(self, repo_path: str, resources_dir: str) -> str:
        rapport = self._development_rules_analyzer.analyze(repo_path)
        contenu = rapport.to_markdown_fragment()
        self._writer.write(resources_dir, NOM_FICHIER_DEVELOPMENT_RULES, contenu)
        return contenu
    def update_resource(self, resources_dir: str, resource_name: str, new_content: str) -> None:
        """Permet de modifier une Resource après sa génération initiale (ou d'en créer une nouvelle) -- réutilise le même writer."""
        self._writer.write(resources_dir, resource_name, new_content)