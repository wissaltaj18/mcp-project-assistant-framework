"""Entité représentant une Resource (fichier .md) une fois chargée en mémoire."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Resource:
    """
    Une Resource chargée, prête à être utilisée par un Prompt.
    frozen=True car une Resource, une fois chargée, ne devrait pas être
    modifiée en mémoire (on recharge une nouvelle instance si le fichier change).
    """

    project_name: str
    name: str
    content: str

    def is_empty(self) -> bool:
        return not self.content.strip()