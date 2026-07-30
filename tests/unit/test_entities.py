"""Tests unitaires des entités du domaine (core/entities/)."""

import pytest

from core.entities.resource import Resource
from core.entities.prompt_template import PromptTemplate
from core.entities.tool_definition import ToolDefinition
from core.entities.generation_request import GenerationRequest
from core.value_objects.project_identifier import ProjectIdentifier
from core.value_objects.resource_path import ResourcePath


def test_resource_is_empty_detecte_contenu_vide():
    resource = Resource(project_name="aegisai", name="test.md", content="   ")
    assert resource.is_empty() is True


def test_resource_is_empty_detecte_contenu_present():
    resource = Resource(project_name="aegisai", name="test.md", content="# Titre")
    assert resource.is_empty() is False


def test_prompt_template_render_assemble_instruction_et_resources():
    template = PromptTemplate(
        name="test_prompt",
        description="Test",
        template_text="Génère {page_name}.",
        required_resource_names=["business_rules.md"],
    )
    resultat = template.render({"business_rules.md": "Contenu des règles"}, page_name="Login")

    assert "Login" in resultat
    assert "Contenu des règles" in resultat


def test_prompt_template_render_gere_resource_manquante():
    template = PromptTemplate(
        name="test_prompt",
        description="Test",
        template_text="Génère {page_name}.",
        required_resource_names=["absente.md"],
    )
    resultat = template.render({}, page_name="Login")
    assert "introuvable" in resultat


def test_tool_definition_detecte_argument_manquant():
    tool = ToolDefinition(
        name="create_file",
        description="Crée un fichier",
        parameters_schema={"required": ["path", "content"]},
    )
    erreurs = tool.validate_arguments({"path": "x.py"})
    assert erreurs == ["Argument obligatoire manquant : 'content'"]


def test_tool_definition_valide_si_tous_arguments_presents():
    tool = ToolDefinition(
        name="create_file",
        description="Crée un fichier",
        parameters_schema={"required": ["path"]},
    )
    erreurs = tool.validate_arguments({"path": "x.py"})
    assert erreurs == []


def test_generation_request_describe():
    request = GenerationRequest(
        project_name="aegisai", prompt_name="generate_login", arguments={"page_name": "Login"}
    )
    assert "aegisai" in request.describe()
    assert "generate_login" in request.describe()


def test_project_identifier_accepte_nom_valide():
    pid = ProjectIdentifier("aegisai")
    assert str(pid) == "aegisai"


def test_project_identifier_refuse_nom_invalide():
    with pytest.raises(ValueError):
        ProjectIdentifier("Ae Gis !!")


def test_resource_path_refuse_extension_non_md():
    pid = ProjectIdentifier("aegisai")
    with pytest.raises(ValueError):
        ResourcePath(project=pid, resource_name="fichier.txt")


def test_resource_path_refuse_path_traversal():
    pid = ProjectIdentifier("aegisai")
    with pytest.raises(ValueError):
        ResourcePath(project=pid, resource_name="../secret.md")