"""Utilitaires techniques purs pour manipuler du texte."""

import re


def slugify(text: str) -> str:
    """Convertit un texte libre en identifiant propre (minuscules, tirets)."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def truncate(text: str, max_length: int = 100) -> str:
    """Coupe un texte trop long, en ajoutant '...' si nécessaire."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
_RUN_COMMAND_LANGS = {"bash", "sh", "shell", "powershell", "cmd", "console"}


def extract_code_block(text: str) -> str:
    """
    Extrait le bloc de code le plus pertinent d'une réponse LLM. Ignore les
    petits blocs de commande (bash/shell de 3 lignes ou moins, type
    "uvicorn main:app --reload"), priorise un bloc explicitement tagué
    python, sinon le plus long bloc de code restant. Si le LLM n'a mis
    aucune balise autour du vrai code (ça arrive), renvoie le texte nettoyé
    des commandes plutôt que rien du tout.
    """
    blocs = list(re.finditer(r"```(\w*)\n(.*?)```", text, re.DOTALL))
    if not blocs:
        return text.strip()

    blocs_code = []
    texte_sans_blocs_commande = text
    for m in blocs:
        langue = m.group(1).lower()
        contenu = m.group(2)
        nb_lignes = len(contenu.strip().splitlines())
        est_commande_courte = langue in _RUN_COMMAND_LANGS and nb_lignes <= 3
        if est_commande_courte:
            texte_sans_blocs_commande = texte_sans_blocs_commande.replace(m.group(0), "")
        else:
            blocs_code.append((langue, contenu))

    for langue, contenu in blocs_code:
        if langue == "python":
            return contenu.strip()

    if blocs_code:
        plus_long = max(blocs_code, key=lambda b: len(b[1]))
        return plus_long[1].strip()

    return texte_sans_blocs_commande.strip()