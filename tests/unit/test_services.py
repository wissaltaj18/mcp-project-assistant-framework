"""
Tests unitaires des services applicatifs, avec des doublons de test
(fake implémentations des ports) -- rapides, déterministes, aucune
dépendance à un vrai LLM ni au vrai système de fichiers.
"""

import pytest

from core.ports.resource_reader_port import ResourceReaderPort
from core.ports.llm_provider_port import LLMProviderPort
from core.ports.logger_port import LoggerPort
from core.entities.prompt_template import PromptTemplate
from core.entities.generation_request import GenerationRequest
from resources.resource_validator import ResourceValidator
from services.resource_service import ResourceService
from services.prompt_service import PromptService, PromptNotFoundError
from services.generation_service import GenerationService


class FakeResourceReader(ResourceReaderPort):
    """Double de test : simule des Resources en mémoire, sans toucher au disque."""

    def __init__(self, contenu: dict[str, str]):
        self._contenu = contenu

    def read(self, project_name: str, resource_name: str) -> str:
        if resource_name not in self._contenu:
            raise FileNotFoundError(f"'{resource_name}' introuvable")
        return self._contenu[resource_name]

    def list_available(self, project_name: str) -> list[str]:
        return list(self._contenu.keys())


class FakeLogger(LoggerPort):
    """Double de test : ne fait rien, juste pour satisfaire l'interface."""

    def info(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


class FakeLLM(LLMProviderPort):
    """Double de test : simule un LLM sans appel réseau."""

    def __init__(self, disponible: bool = True, reponse: str = "code généré"):
        self._disponible = disponible
        self._reponse = reponse

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        return self._reponse

    def is_available(self) -> bool:
        return self._disponible


@pytest.fixture
def resource_service():
    reader = FakeResourceReader({"business_rules.md": "# Règles\nAlerte à 80%"})
    return ResourceService(reader, ResourceValidator())


def test_resource_service_charge_une_resource(resource_service):
    resource = resource_service.load_resource("aegisai", "business_rules.md")
    assert "Alerte à 80%" in resource.content


def test_resource_service_leve_erreur_si_resource_absente(resource_service):
    with pytest.raises(FileNotFoundError):
        resource_service.load_resource("aegisai", "absente.md")


def test_resource_service_refuse_resource_vide():
    reader = FakeResourceReader({"vide.md": ""})
    service = ResourceService(reader, ResourceValidator())
    with pytest.raises(ValueError):
        service.load_resource("aegisai", "vide.md")


def test_prompt_service_assemble_prompt_avec_resources(resource_service):
    registre = {
        "generate_login": PromptTemplate(
            name="generate_login",
            description="Test",
            template_text="Génère {page_name}.",
            required_resource_names=["business_rules.md"],
        )
    }
    prompt_service = PromptService(resource_service, registre)
    resultat = prompt_service.build_prompt("aegisai", "generate_login", page_name="Login")

    assert "Login" in resultat
    assert "Alerte à 80%" in resultat


def test_prompt_service_leve_erreur_si_prompt_inconnu(resource_service):
    prompt_service = PromptService(resource_service, {})
    with pytest.raises(PromptNotFoundError):
        prompt_service.build_prompt("aegisai", "prompt_inexistant")


def test_generation_service_genere_avec_succes(resource_service):
    registre = {
        "generate_login": PromptTemplate(
            name="generate_login",
            description="Test",
            template_text="Génère {page_name}.",
            required_resource_names=["business_rules.md"],
        )
    }
    prompt_service = PromptService(resource_service, registre)
    generation_service = GenerationService(prompt_service, FakeLLM(), FakeLogger())

    request = GenerationRequest(
        project_name="aegisai", prompt_name="generate_login", arguments={"page_name": "Login"}
    )
    resultat = generation_service.generate(request)
    assert resultat == "code généré"


def test_generation_service_leve_erreur_si_llm_indisponible(resource_service):
    registre = {
        "generate_login": PromptTemplate(
            name="generate_login",
            description="Test",
            template_text="Génère {page_name}.",
            required_resource_names=["business_rules.md"],
        )
    }
    prompt_service = PromptService(resource_service, registre)
    generation_service = GenerationService(prompt_service, FakeLLM(disponible=False), FakeLogger())

    request = GenerationRequest(project_name="aegisai", prompt_name="generate_login", arguments={})
    with pytest.raises(ConnectionError):
        generation_service.generate(request)