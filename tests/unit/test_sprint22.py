"""
Tests Sprint 22 : Prompts spécialisés branchés sur KnowledgeBaseLoader.
Vérifie que chaque Prompt charge les bonnes Resources et produit
un contexte exploitable par l'agent.
"""

from services.knowledge_base_loader import KnowledgeBaseLoader
from services.workspace_service import WorkspaceService
from core.ports.git_port import GitPort


class FakeGitPort(GitPort):
    def get_current_commit_hash(self, p): return None
    def get_changed_files_since(self, p, o): return []
    def clone_repository(self, repo_url, destination_path, branch=None, auth_token=None):
        import os; os.makedirs(destination_path, exist_ok=True); return None


def _setup(tmp_path, workspace_id="e-commerce"):
    from pathlib import Path
    ws = WorkspaceService(FakeGitPort(), str(tmp_path))
    loader = KnowledgeBaseLoader(ws)
    resources_dir = tmp_path / workspace_id / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    return loader, resources_dir


def _ecrire(resources_dir, nom, contenu):
    (resources_dir / nom).write_text(contenu, encoding="utf-8")


def _prompt_setup_workspace(repo_url: str, branch: str = "", auth_token: str = "") -> str:
    branche_txt = f" sur la branche {branch}" if branch else ""
    token_txt = f" avec le token d'authentification {auth_token}" if auth_token else ""
    return (
        f"Utilise le tool prepare_workspace pour préparer complètement le Workspace "
        f"à partir du dépôt {repo_url}{branche_txt}{token_txt}. "
        f"Exécute-le entièrement, sans me demander de confirmation intermédiaire, "
        f"et donne-moi un seul message récapitulatif à la fin."
    )


def _prompt_implement_feature(loader, workspace_id, feature_description):
    kb = loader.load_context(workspace_id)
    return (
        f"Tu es un ingénieur senior sur ce projet.\n\n{kb}\n\n---\n\n"
        f"## MISSION\nImplémenter : **{feature_description}**\n\n"
        f"## PROCESSUS OBLIGATOIRE\n"
        f"1. Utilise `check_existing_feature`\n"
        f"2. Utilise `get_project_structure`\n"
        f"3. Respecte les CONSTRAINTS\n"
        f"4. Propose un plan via `create_plan`\n"
        f"5. Attends l'accord explicite."
    )


def _prompt_review_code(loader, workspace_id, file_path):
    kb = loader.load_context(
        workspace_id,
        sections=["development_rules.md", "review_checklist.md", "security_rules.md"]
    )
    return (
        f"Tu es un ingénieur senior qui effectue une code review stricte.\n\n{kb}\n\n---\n\n"
        f"## FICHIER À REVIEWER\n`{file_path}`\n\n"
        f"### 1. VIOLATIONS CRITIQUES\n"
        f"### 2. RISQUES DE SÉCURITÉ\n"
        f"### 3. SUGGESTIONS D'AMÉLIORATION\n"
        f"### 4. VERDICT"
    )


def _prompt_fix_bug(loader, workspace_id, bug_description):
    kb = loader.load_context(
        workspace_id,
        sections=["technical_architecture.md", "functional_overview.md", "development_rules.md"]
    )
    return (
        f"Tu es un ingénieur senior en charge du debugging.\n\n{kb}\n\n---\n\n"
        f"## BUG RAPPORTÉ\n{bug_description}\n\n"
        f"## PROCESSUS\n"
        f"1. `get_project_structure`\n2. `read_file`\n3. `create_plan`"
    )


def _prompt_security_review(loader, workspace_id):
    kb = loader.load_context(
        workspace_id,
        sections=["security_rules.md", "engineering_principles.md"]
    )
    return (
        f"Tu es un ingénieur sécurité senior.\n\n{kb}\n\n---\n\n"
        f"## POINTS À VÉRIFIER\n"
        f"1. Gestion des secrets\n2. CSRF\n3. Injections SQL\n"
        f"4. Authentification\n5. Logs\n6. Dépendances vulnérables"
    )


def _prompt_onboard_project(loader, workspace_id):
    kb = loader.load_context(workspace_id)
    return (
        f"Tu es un tech lead qui accueille un nouveau développeur.\n\n{kb}\n\n---\n\n"
        f"## STRUCTURE ATTENDUE\n"
        f"1. Vue d'ensemble\n2. Architecture\n"
        f"3. Vocabulaire métier\n4. Règles non négociables\n"
        f"5. Processus de développement\n6. Pièges courants"
    )


def _prompt_refactor(loader, workspace_id, target_description):
    kb = loader.load_context(
        workspace_id,
        sections=[
            "engineering_principles.md", "architecture_philosophy.md",
            "technical_architecture.md", "development_rules.md",
        ]
    )
    return (
        f"Tu es un ingénieur senior en charge d'un refactoring.\n\n{kb}\n\n---\n\n"
        f"## CIBLE\n{target_description}\n\n"
        f"## PROCESSUS\n1. `read_file`\n2. Identifier les ANTI-PATTERNS\n"
        f"3. `create_plan` sans régression\n4. Attendre l'approbation"
    )


def _prompt_explain_architecture(loader, workspace_id):
    kb = loader.load_context(
        workspace_id,
        sections=["technical_architecture.md", "functional_overview.md"]
    )
    return (
        f"Tu es un ingénieur senior qui explique l'architecture.\n\n{kb}\n\n---\n\n"
        f"## MISSION\n1. Langages et framework\n2. Couches\n"
        f"3. Patterns\n4. Dépendances\n5. Entités métier"
    )


# ── setup_workspace : PAS de KnowledgeBaseLoader ─────────────────────────────

class TestSetupWorkspace:

    def test_contient_lurl_du_depot(self):
        texte = _prompt_setup_workspace("https://github.com/user/repo.git")
        assert "https://github.com/user/repo.git" in texte

    def test_ne_charge_pas_de_knowledge_base(self):
        texte = _prompt_setup_workspace("https://github.com/user/repo.git")
        assert "KNOWLEDGE BASE" not in texte

    def test_contient_instruction_prepare_workspace(self):
        texte = _prompt_setup_workspace("https://github.com/user/repo.git")
        assert "prepare_workspace" in texte

    def test_inclut_la_branche_si_fournie(self):
        texte = _prompt_setup_workspace("https://github.com/user/repo.git", branch="develop")
        assert "develop" in texte

    def test_inclut_le_token_si_fourni(self):
        texte = _prompt_setup_workspace("https://github.com/user/repo.git", auth_token="ghp_xxx")
        assert "ghp_xxx" in texte


# ── implement_feature ─────────────────────────────────────────────────────────

class TestImplementFeature:

    def test_charge_toute_la_knowledge_base(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "technical_architecture.md", "## FACTS\n- Symfony (PHP)")
        _ecrire(resources_dir, "development_rules.md", "## CONSTRAINTS\n- PascalCase")
        texte = _prompt_implement_feature(loader, "e-commerce", "Ajouter un système de promotion")
        assert "KNOWLEDGE BASE DU PROJET" in texte
        assert "Symfony (PHP)" in texte
        assert "PascalCase" in texte

    def test_contient_la_description_de_la_feature(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_implement_feature(loader, "e-commerce", "Ajouter un système de promotion")
        assert "système de promotion" in texte

    def test_impose_create_plan_avant_modification(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_implement_feature(loader, "e-commerce", "Feature X")
        assert "create_plan" in texte

    def test_impose_check_existing_feature(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_implement_feature(loader, "e-commerce", "Feature X")
        assert "check_existing_feature" in texte

    def test_mentionne_les_constraints(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_implement_feature(loader, "e-commerce", "Feature X")
        assert "CONSTRAINTS" in texte

    def test_sans_resources_indique_generer(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_implement_feature(loader, "e-commerce", "Feature X")
        assert "Aucune Resource disponible" in texte


# ── review_code ────────────────────────────────────────────────────────────────

class TestReviewCode:

    def test_charge_development_rules(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "development_rules.md", "## CONSTRAINTS\n- Pas de SQL direct")
        texte = _prompt_review_code(loader, "e-commerce", "src/Controller/CartController.php")
        assert "Pas de SQL direct" in texte

    def test_charge_review_checklist(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "review_checklist.md", "## CHECKLIST_MANDATORY\n- Tests présents")
        texte = _prompt_review_code(loader, "e-commerce", "src/Controller/CartController.php")
        assert "Tests présents" in texte

    def test_charge_security_rules(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "security_rules.md", "## SECURITY_GLOBAL\n- Pas de secrets")
        texte = _prompt_review_code(loader, "e-commerce", "src/Controller/CartController.php")
        assert "Pas de secrets" in texte

    def test_ne_charge_pas_functional_overview(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "functional_overview.md", "## MARKER_UNIQUE_XYZ")
        texte = _prompt_review_code(loader, "e-commerce", "fichier.php")
        assert "MARKER_UNIQUE_XYZ" not in texte

    def test_contient_le_chemin_du_fichier(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_review_code(loader, "e-commerce", "src/Controller/CartController.php")
        assert "src/Controller/CartController.php" in texte

    def test_structure_en_4_sections(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_review_code(loader, "e-commerce", "fichier.php")
        assert "VIOLATIONS CRITIQUES" in texte
        assert "RISQUES DE SÉCURITÉ" in texte
        assert "SUGGESTIONS" in texte
        assert "VERDICT" in texte


# ── fix_bug ────────────────────────────────────────────────────────────────────

class TestFixBug:

    def test_charge_technical_architecture(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "technical_architecture.md", "## FACTS\n- Symfony")
        texte = _prompt_fix_bug(loader, "e-commerce", "Le panier plante au checkout")
        assert "Symfony" in texte

    def test_contient_la_description_du_bug(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_fix_bug(loader, "e-commerce", "Le panier plante au checkout")
        assert "Le panier plante au checkout" in texte

    def test_impose_create_plan(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_fix_bug(loader, "e-commerce", "Bug X")
        assert "create_plan" in texte

    def test_ne_charge_pas_security_rules(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "security_rules.md", "## MARKER_UNIQUE_XYZ")
        texte = _prompt_fix_bug(loader, "e-commerce", "Bug X")
        assert "MARKER_UNIQUE_XYZ" not in texte


# ── security_review ───────────────────────────────────────────────────────────

class TestSecurityReview:

    def test_charge_security_rules(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "security_rules.md", "## SECURITY_GLOBAL\n- Valider les entrées")
        texte = _prompt_security_review(loader, "e-commerce")
        assert "Valider les entrées" in texte

    def test_charge_engineering_principles(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "engineering_principles.md", "## CONSTRAINTS\n- Moindre privilège")
        texte = _prompt_security_review(loader, "e-commerce")
        assert "Moindre privilège" in texte

    def test_contient_points_de_verification(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_security_review(loader, "e-commerce")
        assert "CSRF" in texte or "secrets" in texte.lower()

    def test_ne_charge_pas_review_checklist(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "review_checklist.md", "## MARKER_UNIQUE_XYZ")
        texte = _prompt_security_review(loader, "e-commerce")
        assert "MARKER_UNIQUE_XYZ" not in texte


# ── onboard_project ───────────────────────────────────────────────────────────

class TestOnboardProject:

    def test_charge_toute_la_knowledge_base(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "technical_architecture.md", "## FACTS\n- Symfony")
        _ecrire(resources_dir, "functional_overview.md", "## VOCABULAIRE\n- Cart, Product")
        _ecrire(resources_dir, "development_rules.md", "## CONSTRAINTS\n- PascalCase")
        texte = _prompt_onboard_project(loader, "e-commerce")
        assert "Symfony" in texte
        assert "Cart, Product" in texte
        assert "PascalCase" in texte

    def test_structure_en_6_sections(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_onboard_project(loader, "e-commerce")
        assert "Architecture" in texte
        assert "Pièges courants" in texte or "courants" in texte.lower()


# ── refactor ──────────────────────────────────────────────────────────────────

class TestRefactor:

    def test_charge_engineering_principles_et_architecture(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "engineering_principles.md", "## CONSTRAINTS\n- Composition")
        _ecrire(resources_dir, "architecture_philosophy.md", "## Patterns\n- Hexagonal")
        texte = _prompt_refactor(loader, "e-commerce", "Refactorer CartService")
        assert "Composition" in texte
        assert "Hexagonal" in texte

    def test_ne_charge_pas_security_rules(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "security_rules.md", "## MARKER_UNIQUE_XYZ")
        texte = _prompt_refactor(loader, "e-commerce", "Refactorer CartService")
        assert "MARKER_UNIQUE_XYZ" not in texte

    def test_contient_la_cible(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_refactor(loader, "e-commerce", "Refactorer CartService")
        assert "CartService" in texte

    def test_impose_preservation_du_comportement(self, tmp_path):
        loader, _ = _setup(tmp_path)
        texte = _prompt_refactor(loader, "e-commerce", "Refactorer CartService")
        assert "régression" in texte.lower() or "comportement" in texte.lower()


# ── explain_architecture ──────────────────────────────────────────────────────

class TestExplainArchitecture:

    def test_charge_technical_et_functional(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "technical_architecture.md", "## FACTS\n- Symfony")
        _ecrire(resources_dir, "functional_overview.md", "## VOCABULAIRE\n- Cart")
        texte = _prompt_explain_architecture(loader, "e-commerce")
        assert "Symfony" in texte
        assert "Cart" in texte

    def test_ne_charge_pas_development_rules(self, tmp_path):
        loader, resources_dir = _setup(tmp_path)
        _ecrire(resources_dir, "development_rules.md", "## MARKER_UNIQUE_XYZ")
        texte = _prompt_explain_architecture(loader, "e-commerce")
        assert "MARKER_UNIQUE_XYZ" not in texte