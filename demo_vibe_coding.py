"""
Script de démonstration "vibe coding" : montre en direct les étapes
Reading Resources -> Generating -> Writing files, avec un vrai résultat
écrit sur le disque. Utilise directement le container (pas le protocole
MCP) pour rester simple -- server.py reste le vrai point d'entrée MCP.

Usage :
    python demo_vibe_coding.py aegisai generate_login "Login"
    python demo_vibe_coding.py aegisai generate_backend "BudgetCheck"
"""

import sys
import time

from bootstrap import build_container
from core.entities.generation_request import GenerationRequest
from tools.file_tools import build_project_file_path, infer_output_path
from utils.string_utils import extract_code_block


def main():
    if len(sys.argv) < 4:
        print("Usage : python demo_vibe_coding.py <projet> <prompt> <page_name>")
        print('Exemple : python demo_vibe_coding.py aegisai generate_login "Login"')
        return

    project_name, prompt_name, page_name = sys.argv[1], sys.argv[2], sys.argv[3]

    container = build_container()

    print(f"\n📖 Reading Resources...")
    try:
        resources_requises = container.prompt_service.get_required_resources(prompt_name)
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return

    for nom in resources_requises:
        print(f"   └─ {nom} ✓")
        time.sleep(0.2)

    print(f"\n🧠 Generating... (patience, ça peut prendre du temps selon le LLM utilisé)")
    request = GenerationRequest(
        project_name=project_name, prompt_name=prompt_name, arguments={"page_name": page_name}
    )
    try:
        resultat_brut = container.orchestrator.dispatch(request)
    except (ConnectionError, ValueError) as e:
        print(f"❌ Erreur : {e}")
        return

    code = extract_code_block(resultat_brut)

    print(f"\n✍️  Writing files...")
    chemin_relatif = infer_output_path(prompt_name, page_name)
    chemin_complet = build_project_file_path(
        container.settings.generated_projects_dir, project_name, chemin_relatif
    )
    container.file_system.create_file(chemin_complet, code)
    print(f"   └─ {chemin_complet} ✓")

    print(f"\n✅ Terminé ! Ouvre {chemin_complet} dans VS Code.\n")


if __name__ == "__main__":
    main()