"""
Lecture de la configuration générale du framework.
Un seul endroit centralise les chemins et paramètres -- si demain on
change l'emplacement des projets générés, on modifie ce fichier, rien d'autre.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FrameworkSettings:
    generated_projects_dir: str
    active_llm_provider: str

    @classmethod
    def from_env(cls) -> "FrameworkSettings":
        return cls(
            generated_projects_dir=os.getenv("GENERATED_PROJECTS_DIR", "generated_projects"),
            active_llm_provider=os.getenv("ACTIVE_LLM_PROVIDER", "ollama_qwen"),
        )