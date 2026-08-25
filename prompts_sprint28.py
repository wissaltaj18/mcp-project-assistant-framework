"""
Logique des 2 nouvelles fonctionnalités Sprint 28 :
  - implement_from_jira_ticket (Prompt)
  - add_jira_comment (Tool)

Isolée en module testable, indépendant de server.py et FastMCP.
"""

_MOTS_AMBIGUS = {
    "fix", "bug", "update", "change", "modify", "modif", "modifier",
    "ajouter", "add", "improve", "ameliorer", "corriger", "correction",
    "todo", "tbd", "wip",
}

_NB_MOTS_MIN_TITRE = 4


def _titre_est_ambigu(titre: str) -> bool:
    mots = [m.lower().strip(".,!?") for m in titre.split() if len(m) > 2]
    if len(mots) < _NB_MOTS_MIN_TITRE:
        return True
    mots_significatifs = [m for m in mots if m not in _MOTS_AMBIGUS]
    return len(mots_significatifs) < 2


def _construire_mission(ticket: dict) -> str:
    titre = ticket.get("titre", "").strip()
    description = ticket.get("description", "").strip()
    if description and description != "Aucune description.":
        return f"{titre}\n\nDétails du ticket :\n{description}"
    return titre


def prompt_implement_from_jira_ticket(
    workspace_id: str,
    ticket_id: str,
    jira_service,
    kb_loader,
) -> str:
    if jira_service is None:
        return (
            "Jira non configuré. Ajoute JIRA_BASE_URL, JIRA_EMAIL et JIRA_API_TOKEN "
            "dans ton fichier .env, puis relance le serveur MCP."
        )

    try:
        ticket = jira_service.get_ticket(ticket_id)
    except FileNotFoundError:
        return (
            f"Ticket '{ticket_id}' introuvable sur Jira. "
            "Vérifie l'ID du ticket et le projet."
        )
    except PermissionError as e:
        return f"Erreur d'authentification Jira : {e}"
    except (ConnectionError, TimeoutError) as e:
        return f"Erreur réseau Jira : {e}"

    titre = ticket.get("titre", "").strip()
    if _titre_est_ambigu(titre):
        return (
            f"Le titre du ticket {ticket_id} est peu explicite : \"{titre}\".\n"
            "Précise ce que tu attends avant de continuer, "
            "ou enrichis la description du ticket dans Jira."
        )

    mission = _construire_mission(ticket)
    kb = kb_loader.load_context(workspace_id)
    ticket_md = jira_service.format_ticket_markdown(ticket)

    return (
        f"Tu es un ingénieur senior assigné à l'implémentation du ticket Jira suivant.\n\n"
        f"## TICKET JIRA : {ticket_id}\n\n"
        f"{ticket_md}\n\n"
        f"---\n\n"
        f"{kb}\n\n"
        f"---\n\n"
        f"## MISSION\n"
        f"{mission}\n\n"
        f"## PROCESSUS OBLIGATOIRE (dans cet ordre)\n"
        f"1. Utilise `check_existing_feature` pour vérifier qu'une fonctionnalité similaire "
        f"n'existe pas déjà.\n"
        f"2. Utilise `get_project_structure` pour localiser les fichiers concernés.\n"
        f"3. Respecte ABSOLUMENT les CONSTRAINTS de la Knowledge Base ci-dessus.\n"
        f"4. Propose un plan via `create_plan` -- NE MODIFIE JAMAIS sans approbation.\n"
        f"5. Attends l'accord explicite de l'utilisateur.\n"
        f"6. Après exécution approuvée, appelle `add_jira_comment` avec un résumé : "
        f"fichiers modifiés, statut des tests, remarques éventuelles.\n\n"
        f"Si tu identifies un ANTI-PATTERN ou une violation de CONSTRAINTS, "
        f"signale-le AVANT de soumettre le plan.\n"
        f"Ne jamais inventer d'exigences absentes du ticket Jira."
    )


def tool_add_jira_comment(
    ticket_id: str,
    comment: str,
    jira_service,
) -> str:
    if jira_service is None:
        return (
            "Jira non configuré. Impossible d'ajouter un commentaire. "
            "Ajoute JIRA_BASE_URL, JIRA_EMAIL et JIRA_API_TOKEN dans ton .env."
        )

    if not ticket_id or not ticket_id.strip():
        return "Erreur : ticket_id est vide."

    if not comment or not comment.strip():
        return "Erreur : le commentaire est vide."

    try:
        jira_service.add_comment(ticket_id.strip(), comment.strip())
        return (
            f"Commentaire ajouté avec succès sur le ticket {ticket_id}.\n"
            f"Contenu : {comment[:200]}{'...' if len(comment) > 200 else ''}"
        )
    except FileNotFoundError:
        return f"Ticket '{ticket_id}' introuvable sur Jira."
    except PermissionError as e:
        return f"Erreur d'authentification Jira : {e}"
    except (ConnectionError, TimeoutError) as e:
        return f"Erreur réseau Jira : {e}"
    except Exception as e:
        return f"Erreur inattendue lors de l'ajout du commentaire : {e}"