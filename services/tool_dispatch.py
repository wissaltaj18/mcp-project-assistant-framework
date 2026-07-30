"""
Construit le dictionnaire de dispatch {nom_du_tool: fonction réelle} à
partir d'une instance ChatTools -- partagé par tous les agents (Gemini,
Ollama, Claude) pour ne jamais dupliquer cette logique de câblage.

Ne contient AUCUN tool d'écriture directe -- create_plan est la seule
capacité de proposition, jamais d'exécution (voir tool_schemas.py).
"""

from services.chat_tools import ChatTools


def build_dispatch(tools: ChatTools) -> dict:
    return {
        "list_resources": lambda **kw: tools.list_resources(),
        "read_resource": lambda **kw: tools.read_resource(kw["resource_name"]),
        "list_available_generators": lambda **kw: tools.list_available_generators(),
        "get_project_structure": lambda **kw: tools.get_project_structure(),
        "check_existing_feature": lambda **kw: tools.check_existing_feature(kw["feature_name_hint"]),
        "find_project_file": lambda **kw: tools.find_project_file(kw["file_name_hint"]),
        "read_file": lambda **kw: tools.read_file(kw["file_path"]),
        "run_tests": lambda **kw: tools.run_tests(),
        "query_database": lambda **kw: tools.query_database(kw["query"]),
        "get_database_schema": lambda **kw: tools.get_database_schema(),
        "import_external_repository": lambda **kw: tools.import_external_repository(kw["repo_url"]),
        "test_function": lambda **kw: tools.test_function(kw["file_path"], kw["function_name"], kw["arguments"]),
        "index_project": lambda **kw: tools.index_project(),
        "search_knowledge_base": lambda **kw: tools.search_knowledge_base(kw["query"]),
        "create_plan": lambda **kw: tools.create_plan(
            kw["user_request"], kw["resources_consulted"], kw["duplication_check"], kw["steps"]
        ),
    }