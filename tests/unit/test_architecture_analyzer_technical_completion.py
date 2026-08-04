"""Vérifie build_system, entry_point, main_dependencies, config_files -- fixtures génériques."""

import json

from services.architecture_analyzer_service import ArchitectureAnalyzerService


def test_detecte_le_build_system_composer(tmp_path):
    (tmp_path / "composer.json").write_text(json.dumps({"require": {}}))

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.build_system == "Composer (PHP)"


def test_detecte_le_point_entree_reel(tmp_path):
    (tmp_path / "manage.py").write_text("# manage")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.entry_point == "manage.py"


def test_aucun_point_entree_connu_renvoie_none(tmp_path):
    (tmp_path / "un_fichier_quelconque.txt").write_text("rien")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.entry_point is None


def test_liste_les_dependances_principales_depuis_composer(tmp_path):
    (tmp_path / "composer.json").write_text(json.dumps({"require": {"symfony/framework-bundle": "^6.4", "doctrine/orm": "^2.0"}}))

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert "symfony/framework-bundle" in rapport.main_dependencies
    assert "doctrine/orm" in rapport.main_dependencies


def test_limite_les_dependances_a_15(tmp_path):
    fausses_deps = {f"paquet/lib-{i}": "^1.0" for i in range(30)}
    (tmp_path / "composer.json").write_text(json.dumps({"require": fausses_deps}))

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert len(rapport.main_dependencies) == 15


def test_detecte_les_fichiers_de_config_connus(tmp_path):
    (tmp_path / ".env.example").write_text("KEY=value")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert ".env.example" in rapport.config_files


def test_detecte_les_fichiers_dans_le_dossier_config(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "services.yaml").write_text("services:")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    config_normalise = [c.replace("\\", "/") for c in rapport.config_files]
    assert "config/services.yaml" in config_normalise


def test_honnete_quand_rien_nest_detecte(tmp_path):
    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.build_system is None
    assert rapport.entry_point is None
    assert rapport.main_dependencies == []
    assert rapport.config_files == []
    fragment = rapport.to_markdown_fragment()
    assert "Information non disponible" in fragment


def test_scenario_symfony_complet_toutes_les_nouvelles_sections(tmp_path):
    """Scénario réaliste combinant toutes les nouvelles détections en une fois."""
    (tmp_path / "composer.json").write_text(json.dumps({
        "require": {"symfony/framework-bundle": "^6.4", "symfony/console": "^6.4"}
    }))
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "index.php").write_text("<?php")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "services.yaml").write_text("services:")
    (tmp_path / ".env.example").write_text("APP_ENV=dev")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.primary_framework == "Symfony (PHP)"
    assert rapport.build_system == "Composer (PHP)"
    assert rapport.entry_point == "public/index.php"
    assert "symfony/framework-bundle" in rapport.main_dependencies
    assert ".env.example" in rapport.config_files

    fragment = rapport.to_markdown_fragment()
    assert "Système de build" in fragment
    assert "Point d'entrée" in fragment
    assert "Dépendances principales" in fragment
    assert "Fichiers de configuration" in fragment