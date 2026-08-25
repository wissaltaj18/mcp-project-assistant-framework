"""Vérifie DevelopmentRulesAnalyzerService, entièrement déterministe."""

import subprocess

from services.development_rules_analyzer_service import DevelopmentRulesAnalyzerService


def test_detecte_phpunit(tmp_path):
    (tmp_path / "phpunit.xml").write_text("<phpunit></phpunit>")

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.test_framework == "PHPUnit"


def test_detecte_github_actions(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI")

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.ci_system == "GitHub Actions"


def test_detecte_la_convention_pascalcase_majoritaire(tmp_path):
    (tmp_path / "CartController.php").write_text("<?php")
    (tmp_path / "ProductController.php").write_text("<?php")
    (tmp_path / "OrderController.php").write_text("<?php")

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.naming_convention is not None
    assert "PascalCase" in rapport.naming_convention


def test_detecte_la_convention_snake_case_majoritaire(tmp_path):
    (tmp_path / "cart_service.py").write_text("def run(): pass")
    (tmp_path / "product_service.py").write_text("def run(): pass")
    (tmp_path / "order_service.py").write_text("def run(): pass")

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert "snake_case" in rapport.naming_convention


def test_detecte_la_vraie_branche_par_defaut_dun_vrai_depot_git(tmp_path):
    """Test avec un VRAI dépôt Git local -- pas une simulation."""
    subprocess.run(["git", "init", "-b", "develop"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    (tmp_path / "fichier.txt").write_text("contenu")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(tmp_path), capture_output=True, check=True)

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.default_branch == "develop"


def test_pas_de_depot_git_renvoie_none_pour_la_branche(tmp_path):
    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.default_branch is None


def test_gitignore_absent(tmp_path):
    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.gitignore_exists is False
    fragment = rapport.to_markdown_fragment()
    assert "Non" in fragment  # Sprint 23 : ".gitignore présent : Non"


def test_gitignore_present_couvre_env(tmp_path):
    (tmp_path / ".gitignore").write_text("vendor/\n.env\nnode_modules/")

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.gitignore_exists is True
    assert rapport.gitignore_covers_env is True


def test_gitignore_present_mais_ne_couvre_pas_env(tmp_path):
    (tmp_path / ".gitignore").write_text("vendor/\nnode_modules/")

    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.gitignore_exists is True
    assert rapport.gitignore_covers_env is False


def test_honnete_quand_rien_nest_detecte(tmp_path):
    rapport = DevelopmentRulesAnalyzerService().analyze(str(tmp_path))

    assert rapport.test_framework is None
    fragment = rapport.to_markdown_fragment()
    assert "Non détecté" in fragment  # Sprint 23 : nouveau libellé