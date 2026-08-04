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
        "create_workspace": lambda **kw: tools.create_workspace(kw["repo_url"], kw.get("branch"), kw.get("auth_token")),
        "set_active_workspace": lambda **kw: tools.set_active_workspace(kw["workspace_id"]),
        "list_resources": lambda **kw: tools.list_resources(),
        "set_preference": lambda **kw: tools.set_preference(kw["workspace_id"], kw["key"], kw["value"]),
        "update_resource": lambda **kw: tools.update_resource(kw["workspace_id"], kw["resource_name"], kw["new_content"]),
        "prepare_workspace": lambda **kw: tools.prepare_workspace(kw["repo_url"], kw.get("branch"), kw.get("auth_token")),
        "generate_resources": lambda **kw: tools.generate_resources(kw["workspace_id"]),
        "read_resource": lambda **kw: tools.read_resource(kw["resource_name"]),
        "list_available_generators": lambda **kw: tools.list_available_generators(),
        "get_project_structure": lambda **kw: tools.get_project_structure(),
        "check_existing_feature": lambda **kw: tools.check_existing_feature(kw["feature_name_hint"]),
        "find_project_file": lambda **kw: tools.find_project_file(kw["file_name_hint"]),
        "read_file": lambda **kw: tools.read_file(kw["file_path"]),
        "run_tests": lambda **kw: tools.run_tests(),
        "index_workspace": lambda **kw: tools.index_workspace(kw["workspace_id"]),
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