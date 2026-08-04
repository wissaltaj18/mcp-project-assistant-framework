"""Vérifie ResourceGeneratorService et MarkdownResourceWriter, fixtures génériques."""

from infra.markdown_resource_writer import MarkdownResourceWriter
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.resource_generator_service import ResourceGeneratorService


def test_markdown_resource_writer_ecrit_reellement_sur_disque(tmp_path):
    writer = MarkdownResourceWriter()
    writer.write(str(tmp_path / "resources"), "sample.md", "# Titre\ncontenu")

    fichier = tmp_path / "resources" / "sample.md"
    assert fichier.exists()
    assert fichier.read_text(encoding="utf-8") == "# Titre\ncontenu"


def test_markdown_resource_writer_cree_le_dossier_si_absent(tmp_path):
    writer = MarkdownResourceWriter()
    dossier_absent = tmp_path / "nouveau" / "dossier"

    writer.write(str(dossier_absent), "sample.md", "contenu")

    assert dossier_absent.exists()


def test_generate_technical_architecture_ecrit_le_bon_fichier(tmp_path):
    (tmp_path / "repo" / "src").mkdir(parents=True)
    (tmp_path / "repo" / "example.py").write_text("def run(): pass")

    service = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
    contenu_renvoye = service.generate_technical_architecture(
        str(tmp_path / "repo"), str(tmp_path / "resources")
    )

    fichier_ecrit = tmp_path / "resources" / "technical_architecture.md"
    assert fichier_ecrit.exists()
    assert fichier_ecrit.read_text(encoding="utf-8") == contenu_renvoye
    assert "Python" in contenu_renvoye


def test_generate_all_produit_un_dict_avec_la_resource_technique(tmp_path):
    (tmp_path / "repo" / "example.py").parent.mkdir(parents=True)
    (tmp_path / "repo" / "example.py").write_text("def run(): pass")

    service = ResourceGeneratorService(ArchitectureAnalyzerService(), MarkdownResourceWriter())
    resultats = service.generate_all(str(tmp_path / "repo"), str(tmp_path / "resources"))