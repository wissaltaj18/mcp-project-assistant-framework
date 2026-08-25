"""
Charge et consolide les Resources d'un Workspace dans l'ordre
hiérarchique défini -- c'est ce composant qui rend le système
"piloté par la connaissance" : modifier une Resource change
immédiatement le comportement de tous les Prompts qui utilisent
load_context(), sans toucher une ligne de code Python.

Ordre de chargement :
  1. engineering_principles.md   (philosophie globale, manuel)
  2. architecture_philosophy.md  (patterns retenus, manuel)
  3. technical_architecture.md   (faits + BP framework, auto)
  4. functional_overview.md      (contexte métier, auto)
  5. development_rules.md        (règles opérationnelles, auto)
  6. review_checklist.md         (critères de review, auto)
  7. security_rules.md           (règles de sécurité, auto)

Règles de conception :
- Les fichiers absents sont ignorés silencieusement --
  rétrocompatible avec les Workspaces créés avant ce sprint.
- Ce service ne génère jamais, n'écrit jamais -- lecture seule.
- Dépend uniquement de WorkspaceService via son interface publique
  (get_resources_path) -- aucun accès à un attribut privé.
"""

from pathlib import Path
from typing import List, Optional


HIERARCHIE_PAR_DEFAUT: List[str] = [
    "engineering_principles.md",
    "architecture_philosophy.md",
    "technical_architecture.md",
    "functional_overview.md",
    "development_rules.md",
    "review_checklist.md",
    "security_rules.md",
]


class KnowledgeBaseLoader:
    """
    Cas d'usage : consolider les Resources d'un Workspace en un
    contexte unique injectable dans n'importe quel Prompt MCP.
    """

    def __init__(self, workspace_service):
        self._workspace_service = workspace_service

    def load_context(
        self,
        workspace_id: str,
        sections: Optional[List[str]] = None,
    ) -> str:
        """
        Charge les Resources dans l'ordre hiérarchique et renvoie un
        contexte consolidé injectable directement dans un Prompt.

        Args:
            workspace_id: Identifiant du Workspace concerné
            sections: Liste de noms de fichiers à charger.
                      None = toute la hiérarchie par défaut.
                      Utile pour les Prompts spécialisés (ex: code review
                      ne charge pas functional_overview).
        """
        resources_path = Path(
            self._workspace_service.get_resources_path(workspace_id)
        )
        a_charger = sections if sections is not None else HIERARCHIE_PAR_DEFAUT
        sections_chargees = []

        for nom_fichier in a_charger:
            contenu = self._lire_resource(resources_path, nom_fichier)
            if contenu is not None:
                sections_chargees.append(f"### [{nom_fichier}]\n{contenu}")

        if not sections_chargees:
            return (
                f"Aucune Resource disponible pour le Workspace '{workspace_id}'. "
                f"Lance generate_resources pour les créer."
            )

        nb = len(sections_chargees)
        entete = (
            f"## KNOWLEDGE BASE DU PROJET ({nb} Resource(s) chargée(s))\n"
            "_Ces règles et contextes doivent guider TOUTES tes réponses "
            "et propositions sur ce Workspace._"
        )
        return entete + "\n\n" + "\n\n---\n\n".join(sections_chargees)

    def load_section(
        self,
        workspace_id: str,
        resource_name: str,
    ) -> Optional[str]:
        """
        Charge une seule Resource par son nom exact.
        Renvoie None si le fichier est absent ou vide.
        """
        resources_path = Path(
            self._workspace_service.get_resources_path(workspace_id)
        )
        return self._lire_resource(resources_path, resource_name)

    def list_available(self, workspace_id: str) -> List[str]:
        """
        Liste les noms des Resources effectivement présentes sur disque,
        dans l'ordre hiérarchique. Les fichiers hors hiérarchie (ex:
        custom_ddd_rules.md) sont listés après, alphabétiquement.
        """
        resources_path = Path(
            self._workspace_service.get_resources_path(workspace_id)
        )
        if not resources_path.exists():
            return []

        tous = {f.name for f in resources_path.glob("*.md") if f.is_file()}
        dans_hierarchie = [nom for nom in HIERARCHIE_PAR_DEFAUT if nom in tous]
        hors_hierarchie = sorted(tous - set(dans_hierarchie))
        return dans_hierarchie + hors_hierarchie

    def _lire_resource(
        self, resources_path: Path, nom_fichier: str
    ) -> Optional[str]:
        """Lit une Resource et retourne son contenu, ou None si absente/vide."""
        chemin = resources_path / nom_fichier
        if not chemin.exists():
            return None
        try:
            contenu = chemin.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            return None
        return contenu if contenu else None