"""
Sprint 31 -- Prompt orchestrateur jira_workflow.
Connecte : Jira lecture + statut + KB + implement + Sonar + commentaire + cloture.
Sprint 34 : ajout des actions disponibles dans create_plan.
"""

_STATUTS_EN_COURS = {"en cours", "in progress", "in-progress"}
_STATUTS_TERMINES = {"terminé", "terminee", "done", "closed", "résolu", "resolved"}


def _detecter_statut_en_cours(transitions: list) -> str:
    for t in transitions:
        nom = t.get("name", "").strip()
        if nom.lower() in _STATUTS_EN_COURS:
            return nom
    return None


def _detecter_statut_termine(transitions: list) -> str:
    for t in transitions:
        nom = t.get("name", "").strip()
        if nom.lower() in _STATUTS_TERMINES:
            return nom
    return None


def prompt_jira_workflow(
    workspace_id: str,
    ticket_id: str,
    jira_service,
    sonar_service,
    kb_loader,
) -> str:
    if jira_service is None:
        return (
            "Jira non configuré. Ajoute JIRA_BASE_URL, JIRA_EMAIL et "
            "JIRA_API_TOKEN dans ton fichier .env."
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

    try:
        transitions = jira_service.get_transitions(ticket_id)
    except Exception:
        transitions = []

    statut_en_cours = _detecter_statut_en_cours(transitions) or "En cours"
    statut_termine = _detecter_statut_termine(transitions) or "Terminé"

    statut_actuel = ticket.get("statut", "").strip().lower()
    if statut_actuel in _STATUTS_TERMINES:
        return (
            f"Le ticket {ticket_id} est déjà au statut '{ticket['statut']}'. "
            "Aucune action nécessaire."
        )

    titre = ticket.get("titre", "").strip()
    description = ticket.get("description", "").strip()
    mission = titre
    if description and description != "Aucune description.":
        mission = f"{titre}\n\nDétails :\n{description}"

    kb = kb_loader.load_context(workspace_id)

    # Verifier si le ticket a des pieces jointes
    attachments_info = ""
    if jira_service is not None:
        try:
            attachments = jira_service.get_attachments(ticket_id)
            if attachments:
                noms = [a["filename"] for a in attachments]
                attachments_info = (
                    f"\n**Pièces jointes détectées sur {ticket_id}** : {', '.join(noms)}\n"
                    f"→ Appelle `download_jira_attachment('{ticket_id}', '<filename>', '{workspace_id}')` "
                    f"pour télécharger chaque image dans public/ avant de créer le plan.\n"
                )
        except Exception:
            pass

    if sonar_service is not None:
        sonar_info = (
            f"- Après l'exécution du plan, appelle `get_sonar_report` "
            f"pour analyser la qualité du code.\n"
            f"- Si Quality Gate PASS :\n"
            f"  a. DEMANDE confirmation à l'utilisateur avant de pousser : "
            f"'Confirmes-tu le git push vers GitHub ?'\n"
            f"  b. Si confirmé : inclus une étape git_push dans un nouveau plan.\n"
            f"  c. Après push réussi : passe le ticket en '{statut_termine}' via `update_jira_status`.\n"
            f"- Si Quality Gate FAIL : laisse le ticket en '{statut_en_cours}' "
            f"et signale les problèmes dans le commentaire Jira.\n"
        )
    else:
        sonar_info = (
            f"- SonarCloud non configuré.\n"
            f"- DEMANDE confirmation à l'utilisateur avant de pousser.\n"
            f"- Après push réussi : passe le ticket en '{statut_termine}'.\n"
        )

    ticket_md = jira_service.format_ticket_markdown(ticket)

    return (
        f"Tu es un ingénieur senior qui prend en charge le ticket Jira suivant "
        f"de bout en bout.\n\n"
        f"## TICKET JIRA : {ticket_id}\n\n"
        f"{ticket_md}\n\n"
        f"{attachments_info}\n"
        f"---\n\n"
        f"{kb}\n\n"
        f"---\n\n"
        f"## MISSION\n"
        f"{mission}\n\n"
        f"## WORKFLOW OBLIGATOIRE -- exécuter dans cet ordre exact\n\n"
        f"### PHASE 1 — Préparation (automatique)\n"
        f"1. Appelle `update_jira_status('{ticket_id}', '{statut_en_cours}')` "
        f"pour signaler que le travail commence.\n"
        f"2. Si des pièces jointes sont listées ci-dessus : appelle "
        f"`download_jira_attachment` pour chaque image avant de continuer.\n"
        f"3. Appelle `check_existing_feature` pour vérifier qu'il n'existe pas "
        f"de fonctionnalité similaire.\n"
        f"4. Appelle `get_project_structure` pour analyser les fichiers concernés.\n"
        f"5. Respecte ABSOLUMENT toutes les CONSTRAINTS de la Knowledge Base.\n\n"
        f"### PHASE 2 — Plan (soumis à approbation humaine)\n"
        f"6. Appelle `create_plan` avec le plan complet et précis.\n"
        f"   **Actions disponibles dans create_plan :**\n"
        f"   - `modify_file` : modifie un fichier existant\n"
        f"   - `create_file` : crée un nouveau fichier (migration Doctrine, "
        f"nouvelle classe PHP, nouveau template Twig...)\n"
        f"   - `git_push` : commit + push vers GitHub\n"
        f"7. ATTENDS l'approbation explicite de l'utilisateur -- "
        f"Appelle approve_plan dès que le plan est créé — l'approbation de l'utilisateur dans le chat compte comme approbation valide.\n\n"
        f"### PHASE 3 — Exécution (après approbation)\n"
        f"8. Le plan est exécuté via `approve_plan`.\n"
        f"{sonar_info}"
        f"9. Appelle `add_jira_comment('{ticket_id}', ...)` avec un résumé complet :\n"
        f"   - Fichiers modifiés ou créés\n"
        f"   - Images téléchargées depuis Jira (si applicable)\n"
        f"   - Résultat SonarCloud (si disponible)\n"
        f"   - Statut du push Git\n"
        f"   - Statut final du ticket\n\n"
        f"### RÈGLES DE SÉCURITÉ\n"
        f"- Ne jamais faire git push sans confirmation humaine explicite.\n"
        f"- Ne jamais faire git reset --hard.\n"
        f"- Ne jamais passer un ticket en '{statut_termine}' si Quality Gate est FAIL.\n"
        f"- Ne jamais modifier du code hors scope du ticket.\n"
        f"- Ne jamais inventer d'exigences absentes du ticket Jira.\n"
        f"- Toujours signaler les ANTI-PATTERNS détectés AVANT de soumettre le plan.\n"
    )