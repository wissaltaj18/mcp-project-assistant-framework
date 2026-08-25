"""Vérifie que les Prompts MCP sont bien enregistrés dans server.py."""

import asyncio
import server


def test_les_prompts_sont_enregistres():
    prompts = asyncio.run(server.mcp.list_prompts())
    noms = {p.name for p in prompts}
    assert "setup_workspace" in noms
    assert "implement_feature" in noms
    assert "review_code" in noms
    assert "fix_bug" in noms
    assert "security_review" in noms
    assert "onboard_project" in noms
    assert "refactor" in noms
    assert "explain_architecture" in noms


def test_setup_workspace_ne_charge_pas_la_knowledge_base():
    """setup_workspace est le seul Prompt sans KnowledgeBaseLoader."""
    resultat = asyncio.run(server.mcp.get_prompt(
        "setup_workspace",
        {"repo_url": "https://github.com/user/repo.git"}
    ))
    texte = resultat.messages[0].content.text
    assert "https://github.com/user/repo.git" in texte
    assert "KNOWLEDGE BASE" not in texte
    assert "prepare_workspace" in texte


def test_implement_feature_charge_la_knowledge_base():
    """Sans Resources sur disque, implement_feature indique clairement de les générer."""
    resultat = asyncio.run(server.mcp.get_prompt(
        "implement_feature",
        {"workspace_id": "sample", "feature_description": "Ajouter un panier"}
    ))
    texte = resultat.messages[0].content.text
    assert "Ajouter un panier" in texte
    assert "create_plan" in texte
    # Sans Resources, le message indique de les générer
    assert "Aucune Resource disponible" in texte or "KNOWLEDGE BASE" in texte


def test_explain_architecture_charge_la_knowledge_base():
    """Sans Resources sur disque, explain_architecture indique clairement de les générer."""
    resultat = asyncio.run(server.mcp.get_prompt(
        "explain_architecture",
        {"workspace_id": "sample"}
    ))
    texte = resultat.messages[0].content.text
    # Le Prompt est bien branché sur KnowledgeBaseLoader
    assert "Aucune Resource disponible" in texte or "KNOWLEDGE BASE" in texte
    assert "generate_resources" in texte or "MISSION" in texte