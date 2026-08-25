"""
Tests Sprint 28 :
- implement_from_jira_ticket : lit ticket Jira + charge KB + construit Prompt
- add_jira_comment : écrit un commentaire sur un ticket Jira
- Détection d'ambiguïté du titre
- Gestion des erreurs Jira
"""

import pytest
from prompts_sprint28 import (
    prompt_implement_from_jira_ticket,
    tool_add_jira_comment,
    _titre_est_ambigu,
    _construire_mission,
)


# ── Stubs ─────────────────────────────────────────────────────────────────────

class KnowledgeBaseLoaderStub:
    def __init__(self, context="## KNOWLEDGE BASE\n### [technical_architecture.md]\nSymfony"):
        self._context = context

    def load_context(self, workspace_id: str, sections=None) -> str:
        if not workspace_id:
            return "Aucune Resource disponible."
        return self._context


class JiraServiceStub:
    def __init__(self, ticket_data=None, should_fail=False):
        self._ticket_data = ticket_data or {
            "id": "KAN-4",
            "titre": "Ajouter un filtre par categorie sur la page produits",
            "statut": "To Do",
            "type": "Task",
            "priorite": "Medium",
            "projet": "Kanban",
            "assignee": "Non assigne",
            "reporter": "tajwissal63",
            "cree_le": "2026-08-10",
            "mis_a_jour_le": "2026-08-10",
            "labels": [],
            "description": "Aucune description.",
        }
        self._should_fail = should_fail

    def get_ticket(self, ticket_id: str) -> dict:
        if self._should_fail:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")
        return self._ticket_data

    def format_ticket_markdown(self, ticket: dict) -> str:
        return f"# {ticket['id']} — {ticket['titre']}\nStatut : {ticket['statut']}"

    def add_comment(self, ticket_id: str, commentaire: str) -> dict:
        if self._should_fail:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")
        return {"succes": True, "ticket_id": ticket_id, "commentaire": commentaire}


# ── Détection d'ambiguïté du titre ───────────────────────────────────────────

class TestTitreEstAmbigu:

    def test_titre_court_est_ambigu(self):
        assert _titre_est_ambigu("Fix bug") is True

    def test_titre_un_seul_mot_est_ambigu(self):
        assert _titre_est_ambigu("Update") is True

    def test_titre_explicite_non_ambigu(self):
        assert _titre_est_ambigu("Ajouter un filtre par categorie sur la page produits") is False

    def test_titre_4_mots_significatifs_non_ambigu(self):
        assert _titre_est_ambigu("Ajouter barre recherche produits") is False

    def test_titre_vide_est_ambigu(self):
        assert _titre_est_ambigu("") is True

    def test_titre_compose_uniquement_de_mots_generiques(self):
        assert _titre_est_ambigu("Fix bug update correction") is True


# ── Construction de la mission ────────────────────────────────────────────────

class TestConstruireMission:

    def test_utilise_titre_si_pas_de_description(self):
        ticket = {
            "titre": "Ajouter un filtre par categorie",
            "description": "Aucune description.",
        }
        mission = _construire_mission(ticket)
        assert mission == "Ajouter un filtre par categorie"

    def test_combine_titre_et_description_si_presente(self):
        ticket = {
            "titre": "Ajouter un filtre",
            "description": "Le filtre doit etre par categorie et prix.",
        }
        mission = _construire_mission(ticket)
        assert "Ajouter un filtre" in mission
        assert "categorie" in mission

    def test_ne_duplique_pas_le_titre_si_description_vide(self):
        ticket = {"titre": "Ajouter un filtre", "description": ""}
        mission = _construire_mission(ticket)
        assert mission.count("Ajouter un filtre") == 1


# ── implement_from_jira_ticket ────────────────────────────────────────────────

class TestImplementFromJiraTicket:

    def test_retourne_erreur_si_jira_non_configure(self):
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", None, kb)
        assert "non configur" in resultat.lower()
        assert "JIRA_API_TOKEN" in resultat

    def test_retourne_erreur_si_ticket_introuvable(self):
        jira = JiraServiceStub(should_fail=True)
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-999", jira, kb)
        assert "introuvable" in resultat.lower()
        assert "KAN-999" in resultat

    def test_retourne_avertissement_si_titre_ambigu(self):
        jira = JiraServiceStub(ticket_data={
            "id": "KAN-5",
            "titre": "Fix bug",
            "statut": "To Do",
            "type": "Task",
            "priorite": "Medium",
            "projet": "Kanban",
            "assignee": "Non assigne",
            "reporter": "admin",
            "cree_le": "2026-08-10",
            "mis_a_jour_le": "2026-08-10",
            "labels": [],
            "description": "Aucune description.",
        })
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-5", jira, kb)
        assert "peu explicite" in resultat.lower() or "ambigu" in resultat.lower()

    def test_prompt_contient_id_ticket(self):
        jira = JiraServiceStub()
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", jira, kb)
        assert "KAN-4" in resultat

    def test_prompt_contient_titre_du_ticket(self):
        jira = JiraServiceStub()
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", jira, kb)
        assert "filtre par categorie" in resultat.lower()

    def test_prompt_contient_knowledge_base(self):
        jira = JiraServiceStub()
        kb = KnowledgeBaseLoaderStub("## KNOWLEDGE BASE\n### [technical_architecture.md]\nSymfony")
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", jira, kb)
        assert "KNOWLEDGE BASE" in resultat
        assert "Symfony" in resultat

    def test_prompt_contient_processus_obligatoire(self):
        jira = JiraServiceStub()
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", jira, kb)
        assert "create_plan" in resultat
        assert "check_existing_feature" in resultat
        assert "approbation" in resultat.lower()

    def test_prompt_contient_instruction_add_jira_comment(self):
        """Le Prompt doit mentionner add_jira_comment pour le workflow futur."""
        jira = JiraServiceStub()
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", jira, kb)
        assert "add_jira_comment" in resultat

    def test_prompt_interdit_invention_dexigences(self):
        """Le Prompt doit rappeler de ne pas inventer d'exigences."""
        jira = JiraServiceStub()
        kb = KnowledgeBaseLoaderStub()
        resultat = prompt_implement_from_jira_ticket("e-commerce", "KAN-4", jira, kb)
        assert "inventer" in resultat.lower() or "absentes" in resultat.lower()


# ── add_jira_comment ──────────────────────────────────────────────────────────

class TestAddJiraComment:

    def test_retourne_erreur_si_jira_non_configure(self):
        resultat = tool_add_jira_comment("KAN-4", "Implementation terminee.", None)
        assert "non configur" in resultat.lower()

    def test_ajoute_commentaire_avec_succes(self):
        jira = JiraServiceStub()
        resultat = tool_add_jira_comment("KAN-4", "Implementation terminee.", jira)
        assert "KAN-4" in resultat
        assert "KAN-4" in resultat

    def test_retourne_erreur_si_ticket_introuvable(self):
        jira = JiraServiceStub(should_fail=True)
        resultat = tool_add_jira_comment("KAN-999", "Commentaire", jira)
        assert "introuvable" in resultat.lower()

    def test_retourne_erreur_si_commentaire_vide(self):
        jira = JiraServiceStub()
        resultat = tool_add_jira_comment("KAN-4", "", jira)
        assert "vide" in resultat.lower()

    def test_retourne_erreur_si_ticket_id_vide(self):
        jira = JiraServiceStub()
        resultat = tool_add_jira_comment("", "Commentaire", jira)
        assert "vide" in resultat.lower()

    def test_tronque_affichage_si_commentaire_long(self):
        jira = JiraServiceStub()
        long_comment = "x" * 500
        resultat = tool_add_jira_comment("KAN-4", long_comment, jira)
        assert "succès" in resultat or "ajout" in resultat.lower()
        assert "..." in resultat