"""Vérifie que les 3 prompts MCP sont bien enregistrés dans server.py."""

import asyncio

import server


def test_les_3_prompts_sont_enregistres():
    prompts = asyncio.run(server.mcp.list_prompts())
    noms = {p.name for p in prompts}
    assert "explain_architecture" in noms
    assert "review_code" in noms
    assert "check_before_implementing" in noms


def test_explain_architecture_produit_un_texte_avec_le_workspace_id():
    resultat = asyncio.run(server.mcp.get_prompt("explain_architecture", {"workspace_id": "sample"}))
    texte = resultat.messages[0].content.text
    assert "sample" in texte
    assert "technical_architecture.md" in texte