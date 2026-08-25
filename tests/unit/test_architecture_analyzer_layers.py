"""Vérifie la détection des dossiers par couche, fixtures génériques (aucun domaine métier)."""

from services.architecture_analyzer_service import ArchitectureAnalyzerService


def test_detecte_les_4_couches_de_la_specification(tmp_path):
    (tmp_path / "src" / "Controller").mkdir(parents=True)
    (tmp_path / "src" / "Service").mkdir(parents=True)
    (tmp_path / "src" / "Entity").mkdir(parents=True)
    (tmp_path / "src" / "Repository").mkdir(parents=True)

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert "controller" in rapport.layer_folders
    assert "service" in rapport.layer_folders
    assert "entity" in rapport.layer_folders
    assert "repository" in rapport.layer_folders


def test_regroupe_model_et_models_sous_entity(tmp_path):
    (tmp_path / "app" / "models").mkdir(parents=True)

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert "entity" in rapport.layer_folders
    assert "model" not in rapport.layer_folders
    assert any("models" in chemin for chemin in rapport.layer_folders["entity"])


def test_ignore_la_casse_du_nom_de_dossier(tmp_path):
    (tmp_path / "controllers").mkdir()

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert "controller" in rapport.layer_folders


def test_ignore_les_dossiers_techniques_comme_vendor(tmp_path):
    (tmp_path / "vendor" / "some-lib" / "Controller").mkdir(parents=True)

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.layer_folders == {}


def test_aucun_dossier_de_couche_donne_un_dict_vide(tmp_path):
    (tmp_path / "example.py").write_text("def run(): pass")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    assert rapport.layer_folders == {}


def test_to_markdown_fragment_liste_les_couches_detectees(tmp_path):
    (tmp_path / "src" / "Controller").mkdir(parents=True)

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))
    fragment = rapport.to_markdown_fragment()

    # Sprint 19 : la section s'appelle maintenant "Couches architecturales détectées"
    assert "Couches architecturales détectées" in fragment
    assert "Controller" in fragment
    assert "Controller" in fragment.replace("\\", "/")


def test_to_markdown_fragment_honnete_si_aucune_couche_detectee():
    from core.entities.architecture_analysis_report import ArchitectureAnalysisReport
    rapport = ArchitectureAnalysisReport()
    fragment = rapport.to_markdown_fragment()

    # Sprint 19 : le libellé a changé
    assert "Aucune couche détectée" in fragment


def test_scenario_symfony_realiste_avec_plusieurs_couches(tmp_path):
    """Scénario proche d'un vrai projet Symfony -- plusieurs couches, plusieurs fichiers par dossier."""
    (tmp_path / "src" / "Controller").mkdir(parents=True)
    (tmp_path / "src" / "Controller" / "CartController.php").write_text("<?php")
    (tmp_path / "src" / "Service").mkdir(parents=True)
    (tmp_path / "src" / "Service" / "CartService.php").write_text("<?php")
    (tmp_path / "src" / "Entity").mkdir(parents=True)
    (tmp_path / "src" / "Entity" / "Cart.php").write_text("<?php")

    rapport = ArchitectureAnalyzerService().analyze(str(tmp_path))

    controller_normalise = [c.replace("\\", "/") for c in rapport.layer_folders["controller"]]
    service_normalise = [c.replace("\\", "/") for c in rapport.layer_folders["service"]]
    entity_normalise = [c.replace("\\", "/") for c in rapport.layer_folders["entity"]]

    assert controller_normalise == ["src/Controller"]
    assert service_normalise == ["src/Service"]
    assert entity_normalise == ["src/Entity"]