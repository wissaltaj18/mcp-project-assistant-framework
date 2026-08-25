"""
Tests Sprint 21 : KnowledgeBaseLoader -- charge les Resources dans
l'ordre hiérarchique, ignore silencieusement les fichiers absents,
retourne un contexte injectable dans les Prompts.
"""

from services.knowledge_base_loader import KnowledgeBaseLoader, HIERARCHIE_PAR_DEFAUT
from services.workspace_service import WorkspaceService
from core.ports.git_port import GitPort
from infra.markdown_resource_writer import MarkdownResourceWriter


class FakeGitPort(GitPort):
    def get_current_commit_hash(self, p): return None
    def get_changed_files_since(self, p, o): return []
    def clone_repository(self, repo_url, destination_path, branch=None, auth_token=None):
        import os; os.makedirs(destination_path, exist_ok=True); return None


def _construire_loader(tmp_path):
    from services.workspace_service import WorkspaceService
    ws = WorkspaceService(FakeGitPort(), str(tmp_path))
    return KnowledgeBaseLoader(ws), ws


def _ecrire_resource(tmp_path, workspace_id, nom_fichier, contenu):
    from pathlib import Path
    dossier = tmp_path / workspace_id / "resources"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / nom_fichier).write_text(contenu, encoding="utf-8")


class TestOrdreHierarchique:

    def test_hierarchie_par_defaut_contient_7_resources(self):
        assert len(HIERARCHIE_PAR_DEFAUT) == 7

    def test_engineering_principles_en_premier(self):
        assert HIERARCHIE_PAR_DEFAUT[0] == "engineering_principles.md"

    def test_security_rules_en_dernier(self):
        assert HIERARCHIE_PAR_DEFAUT[-1] == "security_rules.md"

    def test_load_context_respecte_lordre_hierarchique(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "technical_architecture.md", "# Tech")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev")
        _ecrire_resource(tmp_path, "ws", "engineering_principles.md", "# Eng")

        contexte = loader.load_context("ws")

        pos_eng = contexte.index("[engineering_principles.md]")
        pos_tech = contexte.index("[technical_architecture.md]")
        pos_dev = contexte.index("[development_rules.md]")
        assert pos_eng < pos_tech < pos_dev


class TestFichiersAbsents:

    def test_ignore_silencieusement_les_fichiers_absents(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev Rules")

        contexte = loader.load_context("ws")

        assert "development_rules.md" in contexte
        assert "technical_architecture.md" not in contexte

    def test_workspace_sans_aucune_resource_retourne_message_explicite(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")

        contexte = loader.load_context("ws")

        assert "Aucune Resource disponible" in contexte
        assert "generate_resources" in contexte

    def test_fichier_vide_ignore(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "technical_architecture.md", "   ")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Contenu reel")

        contexte = loader.load_context("ws")

        assert "technical_architecture.md" not in contexte
        assert "development_rules.md" in contexte


class TestLoadContext:

    def test_contexte_contient_entete_knowledge_base(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev")

        contexte = loader.load_context("ws")

        assert "KNOWLEDGE BASE DU PROJET" in contexte

    def test_contexte_indique_le_nombre_de_resources_chargees(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "technical_architecture.md", "# Tech")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev")

        contexte = loader.load_context("ws")

        assert "2 Resource(s)" in contexte

    def test_charge_uniquement_les_sections_demandees(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "technical_architecture.md", "# Tech")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev")
        _ecrire_resource(tmp_path, "ws", "security_rules.md", "# Secu")

        contexte = loader.load_context(
            "ws",
            sections=["development_rules.md", "security_rules.md"]
        )

        assert "development_rules.md" in contexte
        assert "security_rules.md" in contexte
        assert "technical_architecture.md" not in contexte

    def test_contenu_reel_present_dans_contexte(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(
            tmp_path, "ws", "development_rules.md",
            "## CONSTRAINTS\n- PascalCase obligatoire"
        )

        contexte = loader.load_context("ws")

        assert "PascalCase obligatoire" in contexte

    def test_scenario_workspace_complet_7_resources(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        for nom in HIERARCHIE_PAR_DEFAUT:
            _ecrire_resource(tmp_path, "ws", nom, f"# Contenu de {nom}")

        contexte = loader.load_context("ws")

        assert "7 Resource(s)" in contexte
        for nom in HIERARCHIE_PAR_DEFAUT:
            assert nom in contexte


class TestLoadSection:

    def test_charge_une_resource_precise(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "## CONSTRAINTS\n- Regle 1")

        contenu = loader.load_section("ws", "development_rules.md")

        assert contenu is not None
        assert "Regle 1" in contenu

    def test_retourne_none_si_resource_absente(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")

        contenu = loader.load_section("ws", "fichier_absent.md")

        assert contenu is None

    def test_retourne_none_si_resource_vide(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "")

        contenu = loader.load_section("ws", "development_rules.md")

        assert contenu is None


class TestListAvailable:

    def test_liste_dans_ordre_hierarchique(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "security_rules.md", "# Secu")
        _ecrire_resource(tmp_path, "ws", "engineering_principles.md", "# Eng")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev")

        disponibles = loader.list_available("ws")

        assert disponibles[0] == "engineering_principles.md"
        assert disponibles[-1] == "security_rules.md"

    def test_retourne_liste_vide_si_dossier_absent(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)

        disponibles = loader.list_available("ws-inexistant")

        assert disponibles == []

    def test_inclut_les_resources_hors_hierarchie_apres(self, tmp_path):
        loader, ws = _construire_loader(tmp_path)
        ws.create_workspace("https://example.com/user/ws.git")
        _ecrire_resource(tmp_path, "ws", "development_rules.md", "# Dev")
        _ecrire_resource(tmp_path, "ws", "custom_ddd_rules.md", "# DDD")

        disponibles = loader.list_available("ws")

        assert "development_rules.md" in disponibles
        assert "custom_ddd_rules.md" in disponibles
        assert disponibles.index("development_rules.md") < disponibles.index("custom_ddd_rules.md")