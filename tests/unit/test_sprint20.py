"""Tests Sprint 20 : review_checklist.md, security_rules.md, templates."""

from core.entities.development_rules_report import DevelopmentRulesReport
from core.entities.architecture_analysis_report import ArchitectureAnalysisReport
from core.entities.review_checklist_report import ReviewChecklistReport
from core.entities.security_rules_report import SecurityRulesReport
from services.review_checklist_generator_service import ReviewChecklistGeneratorService
from services.security_rules_generator_service import SecurityRulesGeneratorService
from services.knowledge_base_rules_loader import KnowledgeBaseRulesLoader
from services.template_resource_service import TemplateResourceService


# ── KnowledgeBaseRulesLoader.get_security_rules ─────────────────────────────

class TestGetSecurityRules:

    def test_retourne_regles_globales_sans_framework(self):
        loader = KnowledgeBaseRulesLoader()
        regles = loader.get_security_rules(None)
        assert len(regles) > 0
        assert any("secret" in r.lower() for r in regles)

    def test_retourne_regles_globales_plus_framework(self):
        loader = KnowledgeBaseRulesLoader()
        globales = loader.get_security_rules(None)
        avec_framework = loader.get_security_rules("Symfony (PHP)")
        assert len(avec_framework) > len(globales)
        assert any("CSRF" in r for r in avec_framework)

    def test_framework_inconnu_retourne_seulement_globales(self):
        loader = KnowledgeBaseRulesLoader()
        globales = loader.get_security_rules(None)
        inconnues = loader.get_security_rules("FrameworkInconnu (XYZ)")
        assert globales == inconnues

    def test_regles_fastapi_injectees(self):
        loader = KnowledgeBaseRulesLoader()
        regles = loader.get_security_rules("FastAPI (Python)")
        assert any("Pydantic" in r or "CORS" in r for r in regles)

    def test_regles_aspnetcore_injectees(self):
        loader = KnowledgeBaseRulesLoader()
        regles = loader.get_security_rules("ASP.NET Core (C#)")
        assert any("HTTPS" in r or "Identity" in r or "CSRF" in r for r in regles)


# ── ReviewChecklistGeneratorService ─────────────────────────────────────────

class TestReviewChecklistGenerator:

    def test_genere_checklist_avec_framework_tests(self):
        dev = DevelopmentRulesReport(test_framework="PHPUnit")
        arch = ArchitectureAnalysisReport()
        rapport = ReviewChecklistGeneratorService().generate(dev, arch)
        fragment = rapport.to_markdown_fragment()
        assert "PHPUnit" in fragment
        assert "CHECKLIST_MANDATORY" in fragment

    def test_genere_checklist_sans_tests_detectes(self):
        dev = DevelopmentRulesReport(test_framework=None)
        arch = ArchitectureAnalysisReport()
        rapport = ReviewChecklistGeneratorService().generate(dev, arch)
        fragment = rapport.to_markdown_fragment()
        assert "CHECKLIST_MANDATORY" in fragment
        assert "test" in fragment.lower()

    def test_criteres_par_couche_si_detectees(self):
        dev = DevelopmentRulesReport()
        arch = ArchitectureAnalysisReport(
            layer_folders={"controller": ["src/Controller"], "service": ["src/Service"]}
        )
        rapport = ReviewChecklistGeneratorService().generate(dev, arch)
        fragment = rapport.to_markdown_fragment()
        assert "CHECKLIST_ARCHITECTURE" in fragment
        assert "Controller" in fragment

    def test_criteres_par_pattern_cqrs(self):
        dev = DevelopmentRulesReport()
        arch = ArchitectureAnalysisReport(
            detected_patterns=["cqrs"],
            layer_folders={},
        )
        rapport = ReviewChecklistGeneratorService().generate(dev, arch)
        fragment = rapport.to_markdown_fragment()
        assert "CHECKLIST_PATTERNS" in fragment
        assert "CQRS" in fragment or "cqrs" in fragment.lower()

    def test_checklist_recommandee_contient_linter(self):
        dev = DevelopmentRulesReport(linter="PHP_CodeSniffer")
        arch = ArchitectureAnalysisReport()
        rapport = ReviewChecklistGeneratorService().generate(dev, arch)
        fragment = rapport.to_markdown_fragment()
        assert "PHP_CodeSniffer" in fragment
        assert "CHECKLIST_RECOMMENDED" in fragment

    def test_scenario_symfony_complet(self):
        dev = DevelopmentRulesReport(
            test_framework="PHPUnit",
            linter="PHP_CodeSniffer",
            ci_system="GitHub Actions",
            naming_convention="PascalCase (ex: CartController.php)",
        )
        arch = ArchitectureAnalysisReport(
            primary_framework="Symfony (PHP)",
            layer_folders={
                "controller": ["src/Controller"],
                "service": ["src/Service"],
                "entity": ["src/Entity"],
                "repository": ["src/Repository"],
            },
            detected_patterns=["repository"],
        )
        rapport = ReviewChecklistGeneratorService().generate(dev, arch)
        fragment = rapport.to_markdown_fragment()
        assert "PHPUnit" in fragment
        assert "CHECKLIST_MANDATORY" in fragment
        assert "CHECKLIST_RECOMMENDED" in fragment
        assert "CHECKLIST_ARCHITECTURE" in fragment
        assert "CHECKLIST_PATTERNS" in fragment


# ── SecurityRulesGeneratorService ───────────────────────────────────────────

class TestSecurityRulesGenerator:

    def test_contient_regles_globales(self):
        arch = ArchitectureAnalysisReport(primary_framework=None)
        rapport = SecurityRulesGeneratorService().generate(arch)
        fragment = rapport.to_markdown_fragment()
        assert "SECURITY_GLOBAL" in fragment
        assert len(rapport.global_rules) > 0

    def test_contient_regles_symfony(self):
        arch = ArchitectureAnalysisReport(primary_framework="Symfony (PHP)")
        rapport = SecurityRulesGeneratorService().generate(arch)
        fragment = rapport.to_markdown_fragment()
        assert "SECURITY_FRAMEWORK" in fragment
        assert "Symfony (PHP)" in fragment
        assert any("CSRF" in r for r in rapport.framework_rules)

    def test_framework_inconnu_signale_dans_fragment(self):
        arch = ArchitectureAnalysisReport(primary_framework="Gin (Go)")
        rapport = SecurityRulesGeneratorService().generate(arch)
        fragment = rapport.to_markdown_fragment()
        assert "knowledge_base_rules.json" in fragment

    def test_constraints_toujours_presentes(self):
        arch = ArchitectureAnalysisReport()
        rapport = SecurityRulesGeneratorService().generate(arch)
        fragment = rapport.to_markdown_fragment()
        assert "CONSTRAINTS" in fragment

    def test_regles_globales_pas_dupliquees_dans_framework(self):
        """Les règles globales ne doivent pas apparaître dans framework_rules."""
        arch = ArchitectureAnalysisReport(primary_framework="Django (Python)")
        rapport = SecurityRulesGeneratorService().generate(arch)
        for regle_globale in rapport.global_rules:
            assert regle_globale not in rapport.framework_rules


# ── TemplateResourceService ─────────────────────────────────────────────────

class TestTemplateResourceService:

    def test_cree_les_deux_templates_si_absents(self, tmp_path):
        service = TemplateResourceService()
        crees = service.create_if_absent(str(tmp_path))
        assert "engineering_principles.md" in crees
        assert "architecture_philosophy.md" in crees
        assert (tmp_path / "engineering_principles.md").exists()
        assert (tmp_path / "architecture_philosophy.md").exists()

    def test_ne_cree_pas_si_deja_present(self, tmp_path):
        (tmp_path / "engineering_principles.md").write_text(
            "# Mon contenu custom", encoding="utf-8"
        )
        service = TemplateResourceService()
        crees = service.create_if_absent(str(tmp_path))
        assert "engineering_principles.md" not in crees
        assert "Mon contenu custom" in (
            tmp_path / "engineering_principles.md"
        ).read_text(encoding="utf-8")

    def test_preserve_le_contenu_existant(self, tmp_path):
        contenu_original = "# Mes principes\n- Regle 1\n- Regle 2"
        (tmp_path / "engineering_principles.md").write_text(
            contenu_original, encoding="utf-8"
        )
        service = TemplateResourceService()
        service.create_if_absent(str(tmp_path))
        assert (
            tmp_path / "engineering_principles.md"
        ).read_text(encoding="utf-8") == contenu_original

    def test_templates_contiennent_header_non_ecrasement(self, tmp_path):
        service = TemplateResourceService()
        service.create_if_absent(str(tmp_path))
        for nom in ["engineering_principles.md", "architecture_philosophy.md"]:
            contenu = (tmp_path / nom).read_text(encoding="utf-8")
            assert "JAMAIS" in contenu
            assert "UNE SEULE FOIS" in contenu

    def test_cree_le_dossier_resources_si_absent(self, tmp_path):
        dossier_inexistant = tmp_path / "workspaces" / "mon-projet" / "resources"
        service = TemplateResourceService()
        service.create_if_absent(str(dossier_inexistant))
        assert dossier_inexistant.exists()

    def test_retourne_seulement_les_fichiers_crees(self, tmp_path):
        (tmp_path / "engineering_principles.md").write_text("existant", encoding="utf-8")
        service = TemplateResourceService()
        crees = service.create_if_absent(str(tmp_path))
        assert crees == ["architecture_philosophy.md"]