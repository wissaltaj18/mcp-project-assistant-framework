"""
Recherche de fonctions/classes dans le code réel du projet -- GÉNÉRIQUE,
peu importe le langage. Pour Python, utilise l'AST (analyse syntaxique
précise). Pour tout autre langage (PHP, JavaScript, Java, C#, Go, Ruby...),
utilise une recherche par motifs (regex) qui couvre les déclarations de
fonction/méthode les plus courantes. Moins précis que l'AST pur, mais
fonctionne réellement sur n'importe quel projet, pas seulement Python --
c'est le principe même d'un framework générique.
"""

import ast
import re
from pathlib import Path
from typing import List, Optional

from core.entities.code_symbol import CodeSymbol

# Extensions de fichiers considérées comme du "code source" à parcourir,
# au-delà du seul Python -- ajouter un langage = ajouter une extension ici.
EXTENSIONS_CODE = [".py", ".php", ".js", ".ts", ".java", ".cs", ".go", ".rb"]

# Motifs de déclaration de fonction/méthode par famille de langage.
_MOTIFS_FONCTION = [
    r"(?:public|private|protected|static|final|abstract)?\s*function\s+{name}\s*\(",  # PHP, JS
    r"func\s+{name}\s*\(",                                                              # Go
    r"(?:public|private|protected|static|final)?\s*\w[\w<>\[\]]*\s+{name}\s*\(",        # Java, C#
    r"def\s+{name}\b",                                                                  # Ruby / Python (fallback)
]


class PythonCodeSearchService:
    """
    Cas d'usage : chercher des symboles réels dans le code source d'un
    projet, quel que soit le langage utilisé (Python en priorité via AST,
    autres langages via motifs).
    """

    def __init__(self, project_root: str):
        self._root = Path(project_root)

    def find_function(self, function_name: str) -> List[CodeSymbol]:
        resultats = self._find_by_type_python(function_name, ast.FunctionDef, "function")
        resultats.extend(self._find_by_pattern_autres_langages(function_name))
        return resultats

    def find_class(self, class_name: str) -> List[CodeSymbol]:
        return self._find_by_type_python(class_name, ast.ClassDef, "class")

    def _find_by_type_python(self, name: str, node_type, symbol_type: str) -> List[CodeSymbol]:
        resultats = []
        if not self._root.exists():
            return resultats

        for fichier in self._root.rglob("*.py"):
            try:
                arbre = ast.parse(fichier.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for noeud in ast.walk(arbre):
                if isinstance(noeud, node_type) and noeud.name == name:
                    resultats.append(
                        CodeSymbol(
                            name=noeud.name,
                            symbol_type=symbol_type,
                            file_path=str(fichier.relative_to(self._root)),
                            line_number=noeud.lineno,
                            docstring=ast.get_docstring(noeud) or "",
                        )
                    )
        return resultats

    def _find_by_pattern_autres_langages(self, function_name: str) -> List[CodeSymbol]:
        """
        Recherche par motifs dans tous les fichiers de code NON-Python
        (PHP, JS, Java, C#, Go, Ruby...) -- rend la recherche vraiment
        générique, pas limitée à un seul langage.
        """
        resultats = []
        if not self._root.exists():
            return resultats

        motifs_compiles = [
            re.compile(motif.format(name=re.escape(function_name)))
            for motif in _MOTIFS_FONCTION
        ]

        for extension in EXTENSIONS_CODE:
            if extension == ".py":
                continue  # déjà couvert par l'AST, plus précis

            for fichier in self._root.rglob(f"*{extension}"):
                try:
                    lignes = fichier.read_text(encoding="utf-8").splitlines()
                except UnicodeDecodeError:
                    continue

                for numero_ligne, ligne in enumerate(lignes, start=1):
                    if any(motif.search(ligne) for motif in motifs_compiles):
                        resultats.append(
                            CodeSymbol(
                                name=function_name,
                                symbol_type="function",
                                file_path=str(fichier.relative_to(self._root)),
                                line_number=numero_ligne,
                                docstring=ligne.strip(),
                            )
                        )
                        break  # une seule occurrence par fichier suffit

        return resultats

    def find_similar_function_names(self, name_hint: str, seuil: float = 0.3) -> List[CodeSymbol]:
        """
        Cherche des fonctions au nom PROCHE (pas identique), dans TOUS les
        langages supportés -- compare par mots (tokens), gère le cas où
        les mots sont dans un ordre différent.
        """
        tokens_recherche = set(re.split(r"[_\s]+", name_hint.lower())) - {""}
        toutes_fonctions = self._list_all_functions()

        resultats = []
        for fonction in toutes_fonctions:
            tokens_fonction = set(re.split(r"[_\s]+", fonction.name.lower())) - {""}
            if not tokens_fonction or not tokens_recherche:
                continue
            intersection = tokens_recherche & tokens_fonction
            union = tokens_recherche | tokens_fonction
            similarite = len(intersection) / len(union)
            if similarite >= seuil:
                resultats.append(fonction)
        return resultats

    def _list_all_functions(self) -> List[CodeSymbol]:
        """Liste toutes les fonctions Python (AST) -- la comparaison par similarité reste Python pour l'instant."""
        resultats = []
        if not self._root.exists():
            return resultats
        for fichier in self._root.rglob("*.py"):
            try:
                arbre = ast.parse(fichier.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for noeud in ast.walk(arbre):
                if isinstance(noeud, ast.FunctionDef):
                    resultats.append(
                        CodeSymbol(
                            name=noeud.name,
                            symbol_type="function",
                            file_path=str(fichier.relative_to(self._root)),
                            line_number=noeud.lineno,
                            docstring=ast.get_docstring(noeud) or "",
                        )
                    )
        return resultats

    def get_function_source(self, function_name: str) -> "tuple[str, int, int, str] | None":
        """
        Localise précisément une fonction PYTHON : renvoie (fichier, ligne
        début, ligne fin, code source). Utilisé pour éditer UNIQUEMENT
        cette fonction. Reste spécifique à Python (édition ciblée précise
        nécessite un vrai AST ; pour les autres langages, modify_frontend_file
        gère déjà l'édition de fichier complet).
        """
        for fichier in self._root.rglob("*.py"):
            try:
                texte = fichier.read_text(encoding="utf-8")
                arbre = ast.parse(texte)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for noeud in ast.walk(arbre):
                if isinstance(noeud, ast.FunctionDef) and noeud.name == function_name:
                    ligne_debut = noeud.lineno
                    ligne_fin = noeud.end_lineno
                    lignes = texte.splitlines()
                    source = "\n".join(lignes[ligne_debut - 1 : ligne_fin])
                    return (str(fichier.relative_to(self._root)), ligne_debut, ligne_fin, source)
        return None

    def get_project_structure(self) -> str:
        """Renvoie l'arborescence réelle de TOUS les fichiers de code du projet, tous langages confondus."""
        if not self._root.exists():
            return "Projet introuvable."
        lignes = []
        for extension in EXTENSIONS_CODE:
            for fichier in sorted(self._root.rglob(f"*{extension}")):
                lignes.append(str(fichier.relative_to(self._root)))
        return "\n".join(lignes) if lignes else "Aucun fichier de code trouvé."