"""Vérifie FunctionalOverviewAnalyzerService, entièrement déterministe, avec réutilisation d'ArchitectureAnalyzerService."""

import json

from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.functional_overview_analyzer_service import FunctionalOverviewAnalyzerService


def test_cite_la_description_du_manifeste_sans_la_reformuler(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"description": "Une description exacte du projet"}))

    rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

    assert rapport.description == "Une description exacte du projet"


def test_cite_un_extrait_du_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Titre\n\nUn vrai contenu de README.")

    rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

    assert "Un vrai contenu de README" in rapport.readme_excerpt


def test_honnete_quand_aucune_information_disponible(tmp_path):
    rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

    assert rapport.description is None
    assert rapport.detected_routes is None
    assert rapport.detected_entities == []
    fragment = rapport.to_markdown_fragment()
    assert "Information non disponible" in fragment
    assert "Information non disponible" in fragment or "Aucun README" in fragment


def test_cite_le_contenu_dun_fichier_de_routes_connu(tmp_path):
    (tmp_path / "routes").mkdir()
    (tmp_path / "routes" / "web.php").write_text("<?php\nRoute::get('/cart', [CartController::class, 'index']);")

    rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

    assert "routes/web.php" in rapport.detected_routes
    assert "CartController" in rapport.detected_routes


def test_liste_les_entites_via_reutilisation_de_architecture_analyzer(tmp_path):
    (tmp_path / "src" / "Entity").mkdir(parents=True)
    (tmp_path / "src" / "Entity" / "Cart.php").write_text("<?php class Cart {}")
    (tmp_path / "src" / "Entity" / "Product.php").write_text("<?php class Product {}")

    rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

    assert "Cart" in rapport.detected_entities
    assert "Product" in rapport.detected_entities


def test_accepte_un_architecture_analyzer_injecte_explicitement(tmp_path):
    (tmp_path / "src" / "Entity").mkdir(parents=True)
    (tmp_path / "src" / "Entity" / "User.php").write_text("<?php")

    analyseur_partage = ArchitectureAnalyzerService()
    rapport = FunctionalOverviewAnalyzerService(analyseur_partage).analyze(str(tmp_path))

    assert "User" in rapport.detected_entities


def test_workspace_inexistant_renvoie_un_rapport_vide():
    rapport = FunctionalOverviewAnalyzerService().analyze("/chemin/inexistant")

    assert rapport.description is None
    assert rapport.detected_entities == []


def test_scenario_symfony_complet_description_readme_routes_entites(tmp_path):
    (tmp_path / "composer.json").write_text(json.dumps({"description": "Application de gestion de panier"}))
    (tmp_path / "README.md").write_text("# Panier\n\nGere les produits et commandes.")
    (tmp_path / "routes").mkdir()
    (tmp_path / "routes" / "web.php").write_text("<?php\nRoute::get('/cart', [CartController::class, 'index']);")
    (tmp_path / "src" / "Entity").mkdir(parents=True)
    (tmp_path / "src" / "Entity" / "Cart.php").write_text("<?php")
    (tmp_path / "src" / "Entity" / "Order.php").write_text("<?php")

    rapport = FunctionalOverviewAnalyzerService().analyze(str(tmp_path))

    assert rapport.description == "Application de gestion de panier"
    assert "Gere les produits" in rapport.readme_excerpt
    assert "CartController" in rapport.detected_routes
    assert "Cart" in rapport.detected_entities
    assert "Order" in rapport.detected_entities

    fragment = rapport.to_markdown_fragment()
    assert "POINTS D'ENTRÉE EXISTANTS" in fragment or "ROUTES PAR DOMAINE" in fragment
    assert "VOCABULAIRE MÉTIER" in fragment