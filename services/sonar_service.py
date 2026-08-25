"""
Client SonarCloud -- abstraction HTTP isolée et testable.
Utilise l'API REST SonarCloud v1.
Organisation : wissaltaj18
Project key  : wissaltaj18_E-commerce
"""

from typing import Optional
from config.sonar_config import SonarConfig


METRIQUES_PAR_DEFAUT = [
    "bugs",
    "vulnerabilities",
    "code_smells",
    "coverage",
    "duplicated_lines_density",
    "reliability_rating",
    "security_rating",
    "sqale_rating",
    "alert_status",
    "quality_gate_details",
]

_RATING_LABELS = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"}
_GATE_LABELS = {"OK": "PASS", "ERROR": "FAIL", "WARN": "WARN", "NONE": "N/A"}


class SonarService:

    def __init__(self, config: SonarConfig):
        self._config = config
        self._base_url = config.base_url
        self._auth = (config.token, "")

    def _headers(self) -> dict:
        return {"Accept": "application/json"}

    def get_measures(self, metric_keys: Optional[list] = None) -> dict:
        """Récupère les métriques SonarCloud pour le projet configuré."""
        import requests

        keys = metric_keys or METRIQUES_PAR_DEFAUT
        url = f"{self._base_url}/api/measures/component"
        params = {
            "component": self._config.project_key,
            "metricKeys": ",".join(keys),
        }

        try:
            response = requests.get(
                url,
                auth=self._auth,
                headers=self._headers(),
                params=params,
                timeout=15,
            )
        except requests.ConnectionError:
            raise ConnectionError(
                f"Impossible de joindre SonarCloud ({self._base_url}). "
                "Vérifie ta connexion internet."
            )
        except requests.Timeout:
            raise TimeoutError("La requête SonarCloud a dépassé le délai de 15 secondes.")

        if response.status_code == 401:
            raise PermissionError(
                "Token SonarCloud invalide -- vérifie SONAR_TOKEN dans ton .env."
            )
        if response.status_code == 404:
            raise FileNotFoundError(
                f"Projet SonarCloud '{self._config.project_key}' introuvable. "
                "Vérifie SONAR_PROJECT_KEY et SONAR_ORGANIZATION dans ton .env."
            )

        response.raise_for_status()
        return self._parser_measures(response.json())

    def _parser_measures(self, data: dict) -> dict:
        measures = {}
        component = data.get("component", {})
        for m in component.get("measures", []):
            key = m.get("metric", "")
            value = m.get("value", m.get("period", {}).get("value", "N/A"))
            measures[key] = value
        return measures

    def get_quality_gate(self) -> dict:
        """Récupère le statut du Quality Gate du projet."""
        import requests

        url = f"{self._base_url}/api/qualitygates/project_status"
        params = {"projectKey": self._config.project_key}

        try:
            response = requests.get(
                url,
                auth=self._auth,
                headers=self._headers(),
                params=params,
                timeout=15,
            )
        except requests.ConnectionError:
            raise ConnectionError(f"Impossible de joindre SonarCloud ({self._base_url}).")
        except requests.Timeout:
            raise TimeoutError("Timeout SonarCloud.")

        if response.status_code == 401:
            raise PermissionError("Token SonarCloud invalide.")
        if response.status_code == 404:
            raise FileNotFoundError(
                f"Projet '{self._config.project_key}' introuvable sur SonarCloud."
            )

        response.raise_for_status()
        return self._parser_quality_gate(response.json())

    def _parser_quality_gate(self, data: dict) -> dict:
        ps = data.get("projectStatus", {})
        statut_brut = ps.get("status", "NONE")
        statut = _GATE_LABELS.get(statut_brut, statut_brut)

        conditions = []
        for c in ps.get("conditions", []):
            conditions.append({
                "metrique": c.get("metricKey", ""),
                "statut": "PASS" if c.get("status") == "OK" else "FAIL",
                "valeur_actuelle": c.get("actualValue", "N/A"),
                "seuil": c.get("errorThreshold", "N/A"),
            })

        return {"statut": statut, "conditions": conditions}

    def format_report_markdown(self, measures: dict, quality_gate: dict) -> str:
        """Formate le rapport SonarCloud complet en Markdown."""
        statut_gate = quality_gate.get("statut", "N/A")
        emoji_gate = "✅" if statut_gate == "PASS" else "❌" if statut_gate == "FAIL" else "⚠️"

        def rating(val):
            return _RATING_LABELS.get(str(val), str(val)) if val != "N/A" else "N/A"

        def pct(val):
            return f"{val}%" if val != "N/A" else "N/A"

        lignes = [
            f"# Rapport SonarCloud — {self._config.project_key}",
            "",
            f"## Quality Gate : {emoji_gate} {statut_gate}",
            "",
            "## Métriques principales",
            "",
            "| Métrique | Valeur |",
            "|---|---|",
            f"| Bugs | {measures.get('bugs', 'N/A')} |",
            f"| Vulnérabilités | {measures.get('vulnerabilities', 'N/A')} |",
            f"| Code Smells | {measures.get('code_smells', 'N/A')} |",
            f"| Couverture de tests | {pct(measures.get('coverage', 'N/A'))} |",
            f"| Duplication | {pct(measures.get('duplicated_lines_density', 'N/A'))} |",
            f"| Fiabilité | {rating(measures.get('reliability_rating', 'N/A'))} |",
            f"| Sécurité | {rating(measures.get('security_rating', 'N/A'))} |",
            f"| Maintenabilité | {rating(measures.get('sqale_rating', 'N/A'))} |",
            "",
        ]

        conditions = quality_gate.get("conditions", [])
        if conditions:
            lignes.append("## Conditions du Quality Gate")
            lignes.append("")
            lignes.append("| Métrique | Statut | Valeur | Seuil |")
            lignes.append("|---|---|---|---|")
            for c in conditions:
                emoji = "✅" if c["statut"] == "PASS" else "❌"
                lignes.append(
                    f"| {c['metrique']} | {emoji} {c['statut']} "
                    f"| {c['valeur_actuelle']} | {c['seuil']} |"
                )
            lignes.append("")

        if statut_gate == "PASS":
            lignes.append(
                "> ✅ **Quality Gate PASS** — le code respecte les seuils de qualité définis."
            )
        else:
            lignes.append(
                "> ❌ **Quality Gate FAIL** — des corrections sont nécessaires "
                "avant de passer le ticket en Done."
            )

        return "\n".join(lignes)