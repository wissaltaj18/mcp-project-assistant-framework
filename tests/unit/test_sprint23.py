"""
Tests Sprint 23 :
- PHP-CS-Fixer + PHPStan dans _detecter_linter()
- _analyser_workflow_github_actions() lit le contenu réel des workflows
- ci_steps dans DevelopmentRulesReport enrichit CONSTRAINTS et PREFERENCES
- _detecter_violations_architecturales() détecte Controller -> Repository
"""

from services.development_rules_analyzer_service import DevelopmentRulesAnalyzerService
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from core.entities.development_rules_report import DevelopmentRulesReport
from core.entities.architecture_analysis_report import ArchitectureAnalysisReport


# ── Détection PHP-CS-Fixer et PHPStan ────────────────────────────────────────

class TestDetectionLinter:

    def test_detecte_php_cs_fixer(self, tmp_path):
        (tmp_path / ".php-cs-fixer.php").write_text("<?php return [];")
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert rapport.linter == "PHP-CS-Fixer"

    def test_detecte_php_cs_fixer_dist(self, tmp_path):
        (tmp_path / ".php-cs-fixer.dist.php").write_text("<?php return [];")
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert rapport.linter == "PHP-CS-Fixer"

    def test_detecte_phpstan(self, tmp_path):
        (tmp_path / "phpstan.neon").write_text("parameters:\n  level: 8")
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert rapport.linter == "PHPStan"

    def test_php_cs_fixer_prioritaire_sur_phpstan(self, tmp_path):
        """PHP-CS-Fixer est détecté en premier (ordre de priorité)."""
        (tmp_path / ".php-cs-fixer.php").write_text("<?php return [];")
        (tmp_path / "phpstan.neon").write_text("parameters:")
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert rapport.linter == "PHP-CS-Fixer"

    def test_aucun_linter_retourne_none(self, tmp_path):
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert rapport.linter is None


# ── Analyse du contenu des workflows GitHub Actions ───────────────────────────

class TestAnalyseWorkflow:

    def test_detecte_phpunit_dans_workflow(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "jobs:\n  test:\n    steps:\n      - run: vendor/bin/phpunit"
        )
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert any("PHPUnit" in step for step in rapport.ci_steps)

    def test_detecte_php_cs_fixer_dans_workflow(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "jobs:\n  lint:\n    steps:\n      - run: vendor/bin/php-cs-fixer fix --dry-run"
        )
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert any("PHP-CS-Fixer" in step for step in rapport.ci_steps)

    def test_detecte_plusieurs_etapes(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "jobs:\n  ci:\n    steps:\n"
            "      - run: vendor/bin/phpunit\n"
            "      - run: vendor/bin/php-cs-fixer fix --dry-run\n"
            "      - run: composer install"
        )
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert len(rapport.ci_steps) >= 2

    def test_pas_de_workflow_retourne_liste_vide(self, tmp_path):
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        assert rapport.ci_steps == []

    def test_deduplique_les_etapes(self, tmp_path):
        """Deux fichiers workflow qui exécutent phpunit -> une seule entrée."""
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "steps:\n  - run: phpunit"
        )
        (tmp_path / ".github" / "workflows" / "test.yml").write_text(
            "steps:\n  - run: phpunit"
        )
        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        phpunit_steps = [s for s in rapport.ci_steps if "PHPUnit" in s]
        assert len(phpunit_steps) == 1


# ── Rendu enrichi dans DevelopmentRulesReport ────────────────────────────────

class TestRenduEnrichi:

    def test_constraints_renforcees_si_tests_dans_ci(self):
        rapport = DevelopmentRulesReport(
            test_framework="PHPUnit",
            ci_system="GitHub Actions",
            ci_steps=["PHPUnit (tests)", "PHP-CS-Fixer (lint)"],
        )
        fragment = rapport.to_markdown_fragment()
        assert "automatiquement" in fragment.lower() or "CI" in fragment
        assert "PHPUnit" in fragment

    def test_preferences_citent_les_etapes_ci(self):
        rapport = DevelopmentRulesReport(
            ci_system="GitHub Actions",
            ci_steps=["PHPUnit (tests)", "PHP-CS-Fixer (lint)"],
        )
        fragment = rapport.to_markdown_fragment()
        assert "PHPUnit (tests)" in fragment
        assert "PHP-CS-Fixer (lint)" in fragment

    def test_ci_steps_dans_facts(self):
        rapport = DevelopmentRulesReport(
            ci_system="GitHub Actions",
            ci_steps=["PHPUnit (tests)"],
        )
        fragment = rapport.to_markdown_fragment()
        assert "PHPUnit (tests)" in fragment
        assert "FACTS" in fragment

    def test_compatibilite_sans_ci_steps(self):
        """Rétrocompatibilité : sans ci_steps, le rendu reste valide."""
        rapport = DevelopmentRulesReport(
            test_framework="PHPUnit",
            ci_system="GitHub Actions",
        )
        fragment = rapport.to_markdown_fragment()
        assert "PHPUnit" in fragment
        assert "CONSTRAINTS" in fragment

    def test_scenario_symfony_complet_avec_ci(self, tmp_path):
        (tmp_path / "phpunit.xml").write_text("<phpunit></phpunit>")
        (tmp_path / ".php-cs-fixer.php").write_text("<?php return [];")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "steps:\n  - run: vendor/bin/phpunit\n"
            "  - run: vendor/bin/php-cs-fixer fix --dry-run"
        )
        (tmp_path / ".gitignore").write_text("vendor/\n.env\n")

        rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()

        assert rapport.test_framework == "PHPUnit"
        assert rapport.linter == "PHP-CS-Fixer"
        assert rapport.ci_system == "GitHub Actions"
        assert len(rapport.ci_steps) >= 1
        assert "CONSTRAINTS" in fragment
        assert "PREFERENCES" in fragment


# ── Détection violations architecturales ─────────────────────────────────────

class TestViolationsArchitecturales:

    def test_detecte_import_repository_dans_controller_php(self, tmp_path):
        (tmp_path / "src" / "Controller").mkdir(parents=True)
        (tmp_path / "src" / "Controller" / "CartController.php").write_text(
            "<?php\nuse App\\Repository\\CartRepository;\nclass CartController {}"
        )
        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        assert len(rapport.architectural_violations) > 0
        assert "CartController.php" in rapport.architectural_violations[0]
        assert "CartRepository" in rapport.architectural_violations[0]

    def test_pas_de_violation_si_controller_propre(self, tmp_path):
        (tmp_path / "src" / "Controller").mkdir(parents=True)
        (tmp_path / "src" / "Controller" / "CartController.php").write_text(
            "<?php\nuse App\\Service\\CartService;\nclass CartController {}"
        )
        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        assert rapport.architectural_violations == []

    def test_ignore_les_commentaires(self, tmp_path):
        """Un use dans un commentaire ne doit pas déclencher une violation."""
        (tmp_path / "src" / "Controller").mkdir(parents=True)
        (tmp_path / "src" / "Controller" / "CartController.php").write_text(
            "<?php\n// use App\\Repository\\CartRepository;\nclass CartController {}"
        )
        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        assert rapport.architectural_violations == []

    def test_ignore_les_fichiers_hors_controller(self, tmp_path):
        """Un Service qui importe un Repository est normal, pas une violation."""
        (tmp_path / "src" / "Service").mkdir(parents=True)
        (tmp_path / "src" / "Service" / "CartService.php").write_text(
            "<?php\nuse App\\Repository\\CartRepository;\nclass CartService {}"
        )
        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        assert rapport.architectural_violations == []

    def test_violations_apparaissent_dans_fragment(self, tmp_path):
        (tmp_path / "src" / "Controller").mkdir(parents=True)
        (tmp_path / "src" / "Controller" / "CartController.php").write_text(
            "<?php\nuse App\\Repository\\CartRepository;\nclass CartController {}"
        )
        rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
        fragment = rapport.to_markdown_fragment()
        assert "VIOLATIONS" in fragment

    def test_pas_de_section_violations_si_code_propre(self):
        rapport = ArchitectureAnalysisReport()
        fragment = rapport.to_markdown_fragment()
        assert "VIOLATIONS DETECTEES" not in fragment

    def test_retrocompatibilite_champ_vide_par_defaut(self):
        """Un rapport sans architectural_violations reste valide."""
        rapport = ArchitectureAnalysisReport(
            languages=["PHP"],
            primary_framework="Symfony (PHP)",
        )
        assert rapport.architectural_violations == []
        fragment = rapport.to_markdown_fragment()
        assert "VIOLATIONS" not in fragment