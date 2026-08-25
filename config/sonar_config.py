"""
Configuration SonarCloud -- variables d'environnement uniquement.
Jamais de valeur sensible dans le code source.
"""

import os
from dataclasses import dataclass


@dataclass
class SonarConfig:
    base_url: str
    token: str
    organization: str
    project_key: str

    @classmethod
    def from_env(cls) -> "SonarConfig":
        manquantes = []
        base_url = os.getenv("SONAR_BASE_URL", "https://sonarcloud.io").strip().rstrip("/")
        token = os.getenv("SONAR_TOKEN", "").strip()
        organization = os.getenv("SONAR_ORGANIZATION", "").strip()
        project_key = os.getenv("SONAR_PROJECT_KEY", "").strip()

        if not token:
            manquantes.append("SONAR_TOKEN")
        if not organization:
            manquantes.append("SONAR_ORGANIZATION")
        if not project_key:
            manquantes.append("SONAR_PROJECT_KEY")

        if manquantes:
            raise ValueError(
                f"Variables SonarCloud manquantes : {', '.join(manquantes)}. "
                f"Ajoute-les dans ton fichier .env."
            )

        return cls(
            base_url=base_url,
            token=token,
            organization=organization,
            project_key=project_key,
        )

    def is_configured(self) -> bool:
        return bool(
            os.getenv("SONAR_TOKEN") and
            os.getenv("SONAR_ORGANIZATION") and
            os.getenv("SONAR_PROJECT_KEY")
        )