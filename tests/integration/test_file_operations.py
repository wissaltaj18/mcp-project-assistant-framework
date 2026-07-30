"""
Tests d'intégration : utilisent le VRAI système de fichiers (via tmp_path,
un dossier temporaire fourni par pytest, supprimé automatiquement après
chaque test) -- contrairement aux tests unitaires, pas de doublons ici.
"""

import pytest

from config.settings import FrameworkSettings
from resources.markdown_resource_loader import MarkdownResourceLoader
from tools.file_tools import LocalFileSystem, build_project_file_path
from utils.string_utils import extract_code_block, slugify


@pytest.fixture
def settings_temporaires(tmp_path):
    return FrameworkSettings(generated_projects_dir=str(tmp_path), active_llm_provider="ollama_qwen")


def test_markdown_loader_lit_un_vrai_fichier(tmp_path, settings_temporaires):
    dossier_resources = tmp_path / "aegisai" / "resources"
    dossier_resources.mkdir(parents=True)
    (dossier_resources / "business_rules.md").write_text("# Règles\nAlerte à 80%", encoding="utf-8")

    loader = MarkdownResourceLoader(settings_temporaires)
    contenu = loader.read("aegisai", "business_rules.md")

    assert "Alerte à 80%" in contenu


def test_markdown_loader_liste_les_resources_disponibles(tmp_path, settings_temporaires):
    dossier_resources = tmp_path / "aegisai" / "resources"
    dossier_resources.mkdir(parents=True)
    (dossier_resources / "business_rules.md").write_text("# Test", encoding="utf-8")
    (dossier_resources / "project_context.md").write_text("# Test", encoding="utf-8")

    loader = MarkdownResourceLoader(settings_temporaires)
    disponibles = loader.list_available("aegisai")

    assert disponibles == ["business_rules.md", "project_context.md"]


def test_local_file_system_ecrit_et_relit_un_vrai_fichier(tmp_path):
    fs = LocalFileSystem()
    chemin = str(tmp_path / "src" / "pages" / "login.html")

    fs.create_file(chemin, "<h1>Login</h1>")

    assert fs.file_exists(chemin)
    assert fs.read_file(chemin) == "<h1>Login</h1>"


def test_build_project_file_path_bloque_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        build_project_file_path(str(tmp_path), "aegisai", "../../../etc/passwd")


def test_extract_code_block_avec_bloc_markdown():
    texte = "Voici le code :\n```html\n<h1>Test</h1>\n```\nFin."
    assert extract_code_block(texte) == "<h1>Test</h1>"


def test_slugify_nettoie_un_nom_de_page():
    assert slugify("Dashboard Principal !") == "dashboard-principal"