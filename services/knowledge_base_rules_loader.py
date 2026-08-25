"""
Charge et indexe knowledge_base_rules.json -- source unique de vérité
pour toutes les Best Practices, Anti-Patterns et règles de patterns
architecturaux.

Séparation stricte : ce loader lit les données, il ne les applique pas.
Extensibilité : ajouter un framework ou un pattern = modifier le JSON,
pas ce fichier Python.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

_CHEMIN_PAR_DEFAUT = Path(__file__).parent / "knowledge_base_rules.json"


class KnowledgeBaseRulesLoader:

    def __init__(self, rules_path: Optional[Path] = None):
        chemin = rules_path or _CHEMIN_PAR_DEFAUT
        try:
            with open(chemin, encoding="utf-8") as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {"languages": {}, "frameworks": {}, "patterns": {}}

    def get_language_best_practices(self, language: str) -> List[str]:
        return self._data.get("languages", {}).get(language, {}).get("best_practices", [])

    def get_language_anti_patterns(self, language: str) -> List[str]:
        return self._data.get("languages", {}).get(language, {}).get("anti_patterns", [])

    def get_framework_layer_best_practices(self, framework: str, layer: str) -> List[str]:
        return (
            self._data.get("frameworks", {})
            .get(framework, {})
            .get("layers", {})
            .get(layer, {})
            .get("best_practices", [])
        )

    def get_framework_layer_anti_patterns(self, framework: str, layer: str) -> List[str]:
        return (
            self._data.get("frameworks", {})
            .get(framework, {})
            .get("layers", {})
            .get(layer, {})
            .get("anti_patterns", [])
        )

    def get_all_framework_anti_patterns(self, framework: str) -> List[str]:
        layers = (
            self._data.get("frameworks", {})
            .get(framework, {})
            .get("layers", {})
        )
        tous = []
        for layer_data in layers.values():
            tous.extend(layer_data.get("anti_patterns", []))
        vus = set()
        resultat = []
        for ap in tous:
            if ap not in vus:
                vus.add(ap)
                resultat.append(ap)
        return resultat

    def get_framework_layer_best_practices_for_detected_layers(
        self, framework: str, detected_layers: List[str]
    ) -> Dict[str, List[str]]:
        resultat = {}
        for layer in detected_layers:
            bps = self.get_framework_layer_best_practices(framework, layer)
            if bps:
                resultat[layer] = bps
        return resultat

    def get_pattern_description(self, pattern: str) -> str:
        return self._data.get("patterns", {}).get(pattern, {}).get("description", "")

    def get_pattern_best_practices(self, pattern: str) -> List[str]:
        return self._data.get("patterns", {}).get(pattern, {}).get("best_practices", [])

    def get_pattern_anti_patterns(self, pattern: str) -> List[str]:
        return self._data.get("patterns", {}).get(pattern, {}).get("anti_patterns", [])

    def framework_is_known(self, framework: str) -> bool:
        return framework in self._data.get("frameworks", {})

    def list_known_frameworks(self) -> List[str]:
        return list(self._data.get("frameworks", {}).keys())
    def get_security_rules(self, framework: Optional[str] = None) -> List[str]:
        """
        Retourne les règles de sécurité : règles globales + règles spécifiques
        au framework détecté (si fourni et connu). Toujours dans cet ordre.
        """
        security = self._data.get("security_rules", {})
        regles = list(security.get("global", []))
        if framework:
            regles.extend(security.get(framework, []))
        return regles
    def list_known_patterns(self) -> List[str]:
        return list(self._data.get("patterns", {}).keys())