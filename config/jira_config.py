"""
Configuration Jira -- charge les variables d'environnement avec
validation explicite. Jamais de valeur sensible dans le code source.
"""

import os
from dataclasses import dataclass


@dataclass
class JiraConfig:
    base_url: str
    email: str
    api_token: str

    @classmethod
    def from_env(cls) -> "JiraConfig":
        manquantes = []
        base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
        email = os.getenv("JIRA_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()

        if not base_url:
            manquantes.append("JIRA_BASE_URL")
        if not email:
            manquantes.append("JIRA_EMAIL")
        if not api_token:
            manquantes.append("JIRA_API_TOKEN")

        if manquantes:
            raise ValueError(
                f"Variables d'environnement Jira manquantes : {', '.join(manquantes)}. "
                f"Ajoute-les dans ton fichier .env."
            )

        return cls(base_url=base_url, email=email, api_token=api_token)

    def is_configured(self) -> bool:
        return bool(
            os.getenv("JIRA_BASE_URL") and
            os.getenv("JIRA_EMAIL") and
            os.getenv("JIRA_API_TOKEN")
        )