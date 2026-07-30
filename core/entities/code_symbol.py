"""Entité représentant un symbole trouvé dans le code (fonction, classe, méthode)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodeSymbol:
    """Une fonction ou classe réelle trouvée dans le codebase, avec sa localisation."""

    name: str
    symbol_type: str  # "function" ou "class"
    file_path: str
    line_number: int
    docstring: str

    def describe(self) -> str:
        emplacement = f"{self.file_path}:{self.line_number}"
        return f"{self.symbol_type} '{self.name}' dans {emplacement}"