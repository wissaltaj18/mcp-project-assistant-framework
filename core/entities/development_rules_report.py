"""
Résultat d'une analyse FACTUELLE des règles de développement (aucun LLM).

Sprint 23 : nouveau champ ci_steps (étapes CI détectées dans les workflows),
enrichissement de to_markdown_fragment() avec les étapes CI réelles
dans FACTS, CONSTRAINTS et PREFERENCES.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DevelopmentRulesReport:
    """Faits de règles de développement détectés -- déterministes."""

    test_framework: Optional[str] = None
    linter: Optional[str] = None
    ci_system: Optional[str] = None
    naming_convention: Optional[str] = None
    default_branch: Optional[str] = None
    gitignore_exists: bool = False
    gitignore_covers_env: bool = False
    ci_steps: List[str] = field(default_factory=list)

    def to_markdown_fragment(self) -> str:
        lignes = ["# Règles de développement — Knowledge Base", ""]

        lignes.append("## FACTS — Éléments détectés automatiquement")
        lignes.append("")
        lignes.append(f"- **Framework de tests** : {self.test_framework or 'Non détecté'}")
        lignes.append(f"- **Linter** : {self.linter or 'Non détecté'}")
        lignes.append(f"- **CI** : {self.ci_system or 'Non détectée'}")
        if self.ci_steps:
            lignes.append(f"- **Étapes CI configurées** : {', '.join(self.ci_steps)}")
        lignes.append(f"- **Convention de nommage** : {self.naming_convention or 'Non détectée'}")
        lignes.append(f"- **Branche par défaut** : {self.default_branch or 'Non détectée'}")
        lignes.append(f"- **.gitignore présent** : {'Oui' if self.gitignore_exists else 'Non'}")
        if self.gitignore_exists:
            lignes.append(
                f"- **.gitignore couvre .env** : "
                f"{'Oui' if self.gitignore_covers_env else 'Non — risque de fuite de secrets'}"
            )

        constraints = self._construire_constraints()
        if constraints:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## CONSTRAINTS — Règles non négociables")
            lignes.extend(f"- {c}" for c in constraints)

        preferences = self._construire_preferences()
        if preferences:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## PREFERENCES — Conventions recommandées")
            lignes.extend(f"- {p}" for p in preferences)

        risques = self._construire_risques()
        if risques:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## RISQUES — Points d'attention détectés")
            lignes.extend(f"- {r}" for r in risques)

        open_questions = self._construire_open_questions()
        if open_questions:
            lignes.append("")
            lignes.append("---")
            lignes.append("")
            lignes.append("## OPEN QUESTIONS — Décisions non encore prises")
            lignes.extend(f"- {q}" for q in open_questions)

        return "\n".join(lignes)

    def _construire_constraints(self) -> List[str]:
        constraints = []
        if self.test_framework:
            tests_dans_ci = any(
                self.test_framework.lower() in step.lower()
                for step in self.ci_steps
            )
            if tests_dans_ci:
                constraints.append(
                    f"Tout nouveau code DOIT avoir des tests {self.test_framework} -- "
                    f"vérifiés automatiquement par la CI ({self.ci_system}). "
                    f"Aucune PR ne peut merger si les tests échouent."
                )
            else:
                constraints.append(
                    f"Tout nouveau code doit être couvert par des tests {self.test_framework}. "
                    "Aucune pull request sans tests associés."
                )
        if self.linter:
            linter_dans_ci = any(
                self.linter.lower().replace("-", "") in step.lower().replace("-", "")
                for step in self.ci_steps
            )
            if linter_dans_ci:
                constraints.append(
                    f"{self.linter} est vérifié automatiquement par la CI -- "
                    "le code doit passer sans erreur avant tout commit."
                )
            else:
                constraints.append(
                    f"{self.linter} est configuré -- respecter ses règles avant tout commit."
                )
        if self.naming_convention:
            convention = self.naming_convention.split(" ")[0]
            constraints.append(
                f"Convention de nommage OBLIGATOIRE : {convention} "
                f"(détectée : {self.naming_convention})."
            )
        if self.default_branch:
            constraints.append(
                f"La branche cible pour les Pull Requests est `{self.default_branch}`. "
                "Ne jamais pousser directement sur cette branche."
            )
        return constraints

    def _construire_preferences(self) -> List[str]:
        preferences = []
        if self.ci_system and self.ci_steps:
            preferences.append(
                f"La CI ({self.ci_system}) exécute automatiquement : "
                f"{', '.join(self.ci_steps)}. "
                "Vérifier que ces étapes passent localement avant tout push."
            )
        elif self.ci_system:
            preferences.append(
                f"La CI ({self.ci_system}) doit passer au vert avant tout merge."
            )
        if self.gitignore_exists and self.gitignore_covers_env:
            preferences.append(
                "Les fichiers .env sont correctement ignorés par Git. "
                "Ne jamais committer de secrets, tokens ou mots de passe."
            )
        return preferences

    def _construire_risques(self) -> List[str]:
        risques = []
        if not self.gitignore_exists:
            risques.append("CRITIQUE : Aucun .gitignore détecté — risque de commit accidentel.")
        elif not self.gitignore_covers_env:
            risques.append("HAUTE : Le .gitignore ne couvre pas .env — risque de fuite de secrets.")
        if not self.test_framework:
            risques.append("HAUTE : Aucun framework de tests détecté — risque de régression élevé.")
        if not self.ci_system:
            risques.append("MOYENNE : Aucune CI détectée — vérifications qualité non automatisées.")
        return risques

    def _construire_open_questions(self) -> List[str]:
        questions = []
        if not self.test_framework:
            questions.append(
                "Quel framework de tests adopter ? "
                "(Recommandation : PHPUnit pour PHP/Symfony, pytest pour Python)"
            )
        if not self.linter:
            questions.append(
                "Quel linter configurer ? "
                "(Recommandation : PHP-CS-Fixer pour PHP, ESLint pour JS/TS)"
            )
        if not self.ci_system:
            questions.append(
                "Quelle CI mettre en place ? "
                "(Recommandation : GitHub Actions si le dépôt est sur GitHub)"
            )
        if not self.default_branch:
            questions.append(
                "Quelle est la branche principale ? (Convention : `main` ou `master`)"
            )
        return questions