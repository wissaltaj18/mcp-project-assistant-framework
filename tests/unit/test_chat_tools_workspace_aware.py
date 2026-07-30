"""
Vérifie que ChatTools devient Workspace-aware via repo_path, tout en
gardant la rétrocompatibilité totale avec l'ancien mode (project_name
seul, comportement legacy inchangé).
"""

from services.chat_tools import ChatTools


class FakeSettings:
    generated_projects_dir = "generated_projects"


class FakeContainer:
    settings = FakeSettings()


def test_chat_tools_utilise_le_repo_path_explicite_si_fourni(tmp_path):
    (tmp_path / "example.py").write_text("def run():\n    pass")
    tools = ChatTools(FakeContainer(), repo_path=str(tmp_path))
    assert tools._chemin_projet_complet == str(tmp_path)
    assert "example.py" in tools.get_project_structure()


def test_chat_tools_retrocompatible_sans_repo_path():
    tools = ChatTools(FakeContainer(), project_name="demo-rh")
    assert tools._chemin_projet_complet == "generated_projects/demo-rh"


def test_chat_tools_gere_correctement_une_chaine_vide():
    """Cas limite qui justifie if/else explicite plutôt que 'or' : une chaîne vide est une valeur valide, pas une absence."""
    tools = ChatTools(FakeContainer(), repo_path="")
    assert tools._chemin_projet_complet == ""