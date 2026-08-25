"""Vérifie ArchitectureAnalyzerService et son rapport, avec des fixtures génériques."""

import json

from services.architecture_analyzer_service import ArchitectureAnalyzerService


def test_detecte_les_langages_presents(tmp_path):
    (tmp_path / "example.py").write_text("def run(): pass")
    (tmp_path / "sample.js").write_text("function run() {}")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert "Python" in rapport.languages
    assert "JavaScript" in rapport.languages


def test_detecte_le_framework_via_les_vraies_dependances_json(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}))

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.primary_framework == "React (JavaScript/TypeScript)"


def test_ignore_react_mentionne_hors_dependances(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "mon-projet-react-like", "dependencies": {"lodash": "^4.0.0"}}))

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.primary_framework is None


def test_detecte_symfony_via_composer_json_structure(tmp_path):
    (tmp_path / "composer.json").write_text(json.dumps({"require": {"symfony/framework-bundle": "^6.4"}}))

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.primary_framework == "Symfony (PHP)"


def test_composer_json_invalide_ne_fait_pas_planter_lanalyse(tmp_path):
    (tmp_path / "composer.json").write_text("{ ceci n'est pas du JSON valide")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.primary_framework is None


def test_workspace_inexistant_renvoie_un_rapport_vide():
    rapport = ArchitectureAnalyzerService().analyze("/chemin/qui/nexiste/pas")

    assert rapport.languages == []
    assert rapport.primary_framework is None


def test_to_markdown_fragment_commence_par_un_titre_markdown(tmp_path):
    (tmp_path / "example.py").write_text("def run(): pass")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
    fragment = rapport.to_markdown_fragment()

    assert fragment.startswith("# Architecture technique")
    assert "Python" in fragment


def test_to_markdown_fragment_gere_le_cas_sans_rien_detecte():
    from core.entities.architecture_analysis_report import ArchitectureAnalysisReport
    rapport = ArchitectureAnalysisReport()
    fragment = rapport.to_markdown_fragment()

    assert "Aucun langage détecté" in fragment
    # Sprint 19 : le libellé a changé
    assert "Non détecté" in fragment