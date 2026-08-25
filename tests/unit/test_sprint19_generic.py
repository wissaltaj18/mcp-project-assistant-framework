"""
Tests Sprint 19 (révisé) : moteur générique de Knowledge Base.
Fixtures : dépôts minimaux de chaque type (Symfony, FastAPI, NestJS, Spring Boot, ASP.NET Core).
Aucun test ne vérifie du contenu Symfony seulement.
"""

import json
import pytest

from services.knowledge_base_rules_loader import KnowledgeBaseRulesLoader
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from core.entities.architecture_analysis_report import ArchitectureAnalysisReport


# ── KnowledgeBaseRulesLoader ────────────────────────────────────────────────

class TestKnowledgeBaseRulesLoader:

    def setup_method(self):
        self.loader = KnowledgeBaseRulesLoader()

    def test_charge_tous_les_frameworks(self):
        frameworks = self.loader.list_known_frameworks()
        assert "Symfony (PHP)" in frameworks
        assert "FastAPI (Python)" in frameworks
        assert "Spring Boot (Java)" in frameworks
        assert "ASP.NET Core (C#)" in frameworks
        assert "Express (JavaScript/TypeScript)" in frameworks

    def test_charge_tous_les_patterns(self):
        patterns = self.loader.list_known_patterns()
        assert "mvc" in patterns
        assert "repository" in patterns
        assert "cqrs" in patterns
        assert "clean_architecture" in patterns
        assert "hexagonal" in patterns
        assert "ddd" in patterns

    def test_framework_is_known(self):
        assert self.loader.framework_is_known("Symfony (PHP)") is True
        assert self.loader.framework_is_known("UnknownFramework (XYZ)") is False

    def test_bp_par_langage_php(self):
        bps = self.loader.get_language_best_practices("PHP")
        assert len(bps) > 0
        assert any("Composer" in bp or "PSR" in bp for bp in bps)

    def test_bp_par_langage_python(self):
        bps = self.loader.get_language_best_practices("Python")
        assert len(bps) > 0

    def test_bp_fastapi_controller(self):
        bps = self.loader.get_framework_layer_best_practices("FastAPI (Python)", "controller")
        assert len(bps) > 0
        assert any("Pydantic" in bp or "Router" in bp or "Depends" in bp for bp in bps)

    def test_bp_aspnetcore_repository(self):
        bps = self.loader.get_framework_layer_best_practices("ASP.NET Core (C#)", "repository")
        assert len(bps) > 0

    def test_bp_pattern_cqrs(self):
        bps = self.loader.get_pattern_best_practices("cqrs")
        assert len(bps) > 0
        assert any("Command" in bp or "Query" in bp for bp in bps)

    def test_bp_pour_couches_detectees_seulement(self):
        """Si seul 'controller' est détecté, pas de règles pour 'repository'."""
        resultat = self.loader.get_framework_layer_best_practices_for_detected_layers(
            "Symfony (PHP)", ["controller"]
        )
        assert "controller" in resultat
        assert "repository" not in resultat

    def test_degradation_gracieuse_si_fichier_absent(self, tmp_path):
        loader = KnowledgeBaseRulesLoader(rules_path=tmp_path / "inexistant.json")
        assert loader.get_language_best_practices("PHP") == []
        assert loader.list_known_frameworks() == []


# ── Détection de patterns architecturaux ────────────────────────────────────

class TestDetectionPatterns:

    def test_detecte_repository_pattern(self, tmp_path):
        (tmp_path / "src" / "Repository").mkdir(parents=True)
        (tmp_path / "src" / "Repository" / "UserRepository.php").write_text("<?php")

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert "repository" in rapport.detected_patterns

    def test_detecte_cqrs_complet(self, tmp_path):
        (tmp_path / "src" / "Command").mkdir(parents=True)
        (tmp_path / "src" / "Query").mkdir(parents=True)

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert "cqrs" in rapport.detected_patterns

    def test_detecte_cqrs_partiel(self, tmp_path):
        """Commands sans Queries = CQRS partiel, pas confirmé."""
        (tmp_path / "src" / "Command").mkdir(parents=True)

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert "cqrs" not in rapport.detected_patterns
        assert "cqrs" in rapport.partial_patterns

    def test_detecte_hexagonal(self, tmp_path):
        (tmp_path / "src" / "Port").mkdir(parents=True)
        (tmp_path / "src" / "Adapter").mkdir(parents=True)

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert "hexagonal" in rapport.detected_patterns

    def test_detecte_clean_architecture(self, tmp_path):
        for dossier in ["Domain", "Application", "Infrastructure"]:
            (tmp_path / dossier).mkdir()

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert "clean_architecture" in rapport.detected_patterns

    def test_aucun_pattern_sur_depot_vide(self, tmp_path):
        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert rapport.detected_patterns == []
        assert rapport.partial_patterns == []

    def test_ignore_les_patterns_dans_vendor(self, tmp_path):
        (tmp_path / "vendor" / "lib" / "Repository").mkdir(parents=True)

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert "repository" not in rapport.detected_patterns


# ── Généricité du moteur (multi-framework) ───────────────────────────────────

class TestGenericiteMultiFramework:

    def test_symfony_bp_injectees_si_couche_presente(self, tmp_path):
        (tmp_path / "composer.json").write_text(
            json.dumps({"require": {"symfony/framework-bundle": "^6.4"}})
        )
        (tmp_path / "src" / "Controller").mkdir(parents=True)
        (tmp_path / "src" / "Controller" / "HomeController.php").write_text("<?php")

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()

        assert "Symfony (PHP)" in fragment
        assert "BEST PRACTICES" in fragment
        assert "ANTI-PATTERNS" in fragment

    def test_fastapi_detecte_et_bp_injectees(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\nuvicorn")
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "routers").mkdir()
        (tmp_path / "app" / "services").mkdir()

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()

        assert rapport.primary_framework == "FastAPI (Python)"
        assert "FastAPI (Python)" in fragment

    def test_aspnetcore_detecte(self, tmp_path):
        csproj = tmp_path / "MyApp.csproj"
        csproj.write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web">'
            '<ItemGroup><PackageReference Include="Microsoft.AspNetCore.App"/></ItemGroup>'
            '</Project>'
        )

        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

        assert rapport.primary_framework == "ASP.NET Core (C#)"

    def test_framework_inconnu_genere_open_question(self):
        rapport = ArchitectureAnalysisReport(
            languages=["Go"],
            primary_framework="Gin (Go)",
        )
        fragment = rapport.to_markdown_fragment()

        assert "OPEN QUESTIONS" in fragment
        assert "Gin (Go)" in fragment
        assert "knowledge_base_rules.json" in fragment

    def test_framework_connu_pas_d_open_question(self):
        rapport = ArchitectureAnalysisReport(
            languages=["PHP"],
            primary_framework="Symfony (PHP)",
        )
        fragment = rapport.to_markdown_fragment()

        lines_oq = [l for l in fragment.split("\n") if "non encore référencé" in l]
        assert lines_oq == []

    def test_patterns_detectes_apparaissent_dans_fragment(self):
        rapport = ArchitectureAnalysisReport(
            languages=["Python"],
            primary_framework="FastAPI (Python)",
            detected_patterns=["repository", "cqrs"],
            partial_patterns=[],
        )
        fragment = rapport.to_markdown_fragment()

        assert "REPOSITORY" in fragment
        assert "CQRS" in fragment
        assert "BEST PRACTICES — Patterns architecturaux détectés" in fragment

    def test_patterns_partiels_signales_dans_constraints(self):
        rapport = ArchitectureAnalysisReport(
            languages=["Java"],
            primary_framework="Spring Boot (Java)",
            detected_patterns=[],
            partial_patterns=["cqrs"],
        )
        fragment = rapport.to_markdown_fragment()

        assert "CONSTRAINTS" in fragment
        assert "cqrs" in fragment.lower()

    def test_sans_framework_pas_de_bp_framework(self):
        rapport = ArchitectureAnalysisReport(languages=["Python"], primary_framework=None)
        fragment = rapport.to_markdown_fragment()

        assert "BEST PRACTICES — None" not in fragment

    def test_normalise_windows_separators(self):
        """Le chemin src\\Controller (Windows) ne doit pas casser l'affichage."""
        rapport = ArchitectureAnalysisReport(
            languages=["PHP"],
            primary_framework="Symfony (PHP)",
            layer_folders={"controller": ["src\\Controller"]},
        )
        fragment = rapport.to_markdown_fragment()
        assert "Controller" in fragment