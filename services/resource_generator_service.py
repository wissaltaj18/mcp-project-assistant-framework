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

    def generate_all(self, repo_path: str, resources_dir: str) -> Dict[str, str]:
        """Point d'entrée unique : génère les 3 Resources complètes."""
        return {
            NOM_FICHIER_TECHNICAL: self.generate_technical_architecture(repo_path, resources_dir),
            NOM_FICHIER_FUNCTIONAL: self.generate_functional_overview(repo_path, resources_dir),
            NOM_FICHIER_DEVELOPMENT_RULES: self.generate_development_rules(repo_path, resources_dir),
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