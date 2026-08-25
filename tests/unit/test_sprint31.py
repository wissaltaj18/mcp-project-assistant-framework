"""
Tests Sprint 31 : prompt_jira_workflow
- Détection des statuts Jira (français/anglais)
- Ticket déjà terminé
- Jira non configuré
- Ticket introuvable
- Prompt complet avec workflow obligatoire
- Intégration SonarCloud présente ou absente
"""

import pytest
from prompts_sprint31 import (
    prompt_jira_workflow,
    _detecter_statut_en_cours,
    _detecter_statut_termine,
)


# ── Stubs ─────────────────────────────────────────────────────────────────────

class JiraServiceStub:
    def __init__(self, ticket_data=None, transitions=None, should_fail=False):
        self._ticket_data = ticket_data or {
            "id": "KAN-4",
            "titre": "Ajouter un filtre par categorie",
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
        }
        self._transitions = transitions or [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "En cours"},
            {"id": "31", "name": "Terminé"},
        ]
        self._should_fail = should_fail

    def get_ticket(self, ticket_id):
        if self._should_fail:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")
        return self._ticket_data

    def get_transitions(self, ticket_id):
        return self._transitions

    def format_ticket_markdown(self, ticket):
        return f"# {ticket['id']} — {ticket['titre']}\nStatut : {ticket['statut']}"


class KBLoaderStub:
    def load_context(self, workspace_id, sections=None):
        return "## KNOWLEDGE BASE\nSymfony (PHP)\nController → Service → Repository"


class SonarServiceStub:
    pass


# ── Détection statuts ─────────────────────────────────────────────────────────

class TestDetectionStatuts:

    def test_detecte_en_cours_francais(self):
        transitions = [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "En cours"},
            {"id": "31", "name": "Terminé"},
        ]
        assert _detecter_statut_en_cours(transitions) == "En cours"

    def test_detecte_in_progress_anglais(self):
        transitions = [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        assert _detecter_statut_en_cours(transitions) == "In Progress"

    def test_detecte_termine_francais(self):
        transitions = [
            {"id": "21", "name": "En cours"},
            {"id": "31", "name": "Terminé"},
        ]
        assert _detecter_statut_termine(transitions) == "Terminé"

    def test_detecte_done_anglais(self):
        transitions = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        assert _detecter_statut_termine(transitions) == "Done"

    def test_retourne_none_si_statut_absent(self):
        transitions = [{"id": "11", "name": "Review"}]
        assert _detecter_statut_en_cours(transitions) is None
        assert _detecter_statut_termine(transitions) is None

    def test_insensible_a_la_casse(self):
        transitions = [{"id": "21", "name": "IN PROGRESS"}]
        assert _detecter_statut_en_cours(transitions) == "IN PROGRESS"


# ── prompt_jira_workflow ──────────────────────────────────────────────────────

class TestPromptJiraWorkflow:

    def test_retourne_erreur_si_jira_non_configure(self):
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", None, None, KBLoaderStub()
        )
        assert "non configur" in resultat.lower()
        assert "JIRA_API_TOKEN" in resultat

    def test_retourne_erreur_si_ticket_introuvable(self):
        jira = JiraServiceStub(should_fail=True)
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-999", jira, None, KBLoaderStub()
        )
        assert "introuvable" in resultat.lower()
        assert "KAN-999" in resultat

    def test_retourne_message_si_ticket_deja_termine(self):
        jira = JiraServiceStub(ticket_data={
            "id": "KAN-4",
            "titre": "Ticket termine",
            "statut": "Terminé",
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
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "deja" in resultat.lower() or "déjà" in resultat.lower()

    def test_prompt_contient_id_ticket(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "KAN-4" in resultat

    def test_prompt_contient_knowledge_base(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "KNOWLEDGE BASE" in resultat
        assert "Symfony" in resultat

    def test_prompt_contient_workflow_obligatoire(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "update_jira_status" in resultat
        assert "create_plan" in resultat
        assert "approve_plan" in resultat
        assert "add_jira_comment" in resultat
        assert "approbation" in resultat.lower()

    def test_prompt_contient_statut_en_cours_detecte(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "En cours" in resultat

    def test_prompt_contient_statut_termine_detecte(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "Terminé" in resultat

    def test_prompt_contient_sonar_si_configure(self):
        jira = JiraServiceStub()
        sonar = SonarServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, sonar, KBLoaderStub()
        )
        assert "get_sonar_report" in resultat
        assert "Quality Gate" in resultat

    def test_prompt_sans_sonar_mentionne_absence(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "get_sonar_report" not in resultat
        assert (
            "non configur" in resultat.lower()
            or "directement" in resultat.lower()
            or "sans" in resultat.lower()
        )

    def test_prompt_interdit_modification_sans_approbation(self):
        jira = JiraServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "NE MODIFIE JAMAIS" in resultat or "sans approbation" in resultat.lower()

    def test_prompt_interdit_done_si_quality_gate_fail(self):
        jira = JiraServiceStub()
        sonar = SonarServiceStub()
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, sonar, KBLoaderStub()
        )
        assert "FAIL" in resultat
        assert "jamais" in resultat.lower()

    def test_prompt_avec_statuts_anglais(self):
        jira = JiraServiceStub(transitions=[
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ])
        resultat = prompt_jira_workflow(
            "e-commerce", "KAN-4", jira, None, KBLoaderStub()
        )
        assert "In Progress" in resultat
        assert "Done" in resultat