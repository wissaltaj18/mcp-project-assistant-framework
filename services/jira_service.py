"""
Client Jira -- abstraction HTTP isolée et testable.
Utilise l'API REST Jira Cloud v3.
"""

from typing import Optional
from config.jira_config import JiraConfig


class JiraService:

    def __init__(self, config: JiraConfig):
        self._config = config
        self._base_url = config.base_url
        self._auth = (config.email, config.api_token)

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_ticket(self, ticket_id: str) -> dict:
        import requests
        url = f"{self._base_url}/rest/api/3/issue/{ticket_id}"
        try:
            response = requests.get(url, auth=self._auth, headers=self._headers(), timeout=10)
        except requests.ConnectionError:
            raise ConnectionError(
                f"Impossible de joindre Jira ({self._base_url}). "
                "Vérifie ta connexion internet et l'URL Jira."
            )
        except requests.Timeout:
            raise TimeoutError("La requête Jira a dépassé le délai de 10 secondes.")

        if response.status_code == 401:
            raise PermissionError(
                "Authentification Jira invalide -- "
                "vérifie JIRA_EMAIL et JIRA_API_TOKEN dans ton .env."
            )
        if response.status_code == 404:
            raise FileNotFoundError(
                f"Ticket '{ticket_id}' introuvable sur {self._base_url}."
            )
        if response.status_code == 403:
            raise PermissionError(
                f"Accès refusé au ticket '{ticket_id}'."
            )

        response.raise_for_status()
        return self._parser_ticket(response.json())

    def _parser_ticket(self, data: dict) -> dict:
        fields = data.get("fields", {})
        description = self._extraire_texte_adf(fields.get("description"))
        assignee = fields.get("assignee")
        assignee_nom = assignee.get("displayName", "Non assigné") if assignee else "Non assigné"
        reporter = fields.get("reporter")
        reporter_nom = reporter.get("displayName", "Inconnu") if reporter else "Inconnu"
        priority = fields.get("priority")
        priority_nom = priority.get("name", "Non définie") if priority else "Non définie"

        return {
            "id": data.get("key", ""),
            "titre": fields.get("summary", "Sans titre"),
            "statut": fields.get("status", {}).get("name", "Inconnu"),
            "priorite": priority_nom,
            "description": description,
            "assignee": assignee_nom,
            "reporter": reporter_nom,
            "type": fields.get("issuetype", {}).get("name", "Inconnu"),
            "projet": fields.get("project", {}).get("name", "Inconnu"),
            "cree_le": fields.get("created", "")[:10] if fields.get("created") else "",
            "mis_a_jour_le": fields.get("updated", "")[:10] if fields.get("updated") else "",
            "labels": fields.get("labels", []),
        }

    def _extraire_texte_adf(self, adf: Optional[dict]) -> str:
        if adf is None:
            return "Aucune description."
        if isinstance(adf, str):
            return adf
        texte_parts = []
        self._extraire_texte_recursif(adf, texte_parts)
        resultat = " ".join(texte_parts).strip()
        return resultat if resultat else "Aucune description."

    def _extraire_texte_recursif(self, node: dict, parts: list) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "text":
            text = node.get("text", "").strip()
            if text:
                parts.append(text)
        for child in node.get("content", []):
            self._extraire_texte_recursif(child, parts)

    def add_comment(self, ticket_id: str, commentaire: str) -> dict:
        import requests
        url = f"{self._base_url}/rest/api/3/issue/{ticket_id}/comment"
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": commentaire}]
                    }
                ]
            }
        }
        try:
            response = requests.post(url, auth=self._auth, headers=self._headers(), json=body, timeout=10)
        except requests.ConnectionError:
            raise ConnectionError(f"Impossible de joindre Jira ({self._base_url}).")

        if response.status_code == 401:
            raise PermissionError("Authentification Jira invalide.")
        if response.status_code == 404:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")

        response.raise_for_status()
        return {"succes": True, "ticket_id": ticket_id, "commentaire": commentaire}

    def format_ticket_markdown(self, ticket: dict) -> str:
        labels_str = ", ".join(ticket["labels"]) if ticket["labels"] else "Aucun"
        return (
            f"# Ticket Jira : {ticket['id']}\n\n"
            f"## {ticket['titre']}\n\n"
            f"| Champ | Valeur |\n"
            f"|---|---|\n"
            f"| **Statut** | {ticket['statut']} |\n"
            f"| **Type** | {ticket['type']} |\n"
            f"| **Priorité** | {ticket['priorite']} |\n"
            f"| **Projet** | {ticket['projet']} |\n"
            f"| **Assigné** | {ticket['assignee']} |\n"
            f"| **Reporter** | {ticket['reporter']} |\n"
            f"| **Créé le** | {ticket['cree_le']} |\n"
            f"| **Mis à jour** | {ticket['mis_a_jour_le']} |\n"
            f"| **Labels** | {labels_str} |\n\n"
            f"## Description\n\n"
            f"{ticket['description']}\n"
        )
    def get_transitions(self, ticket_id: str) -> list:
        """
        Récupère la liste des transitions disponibles pour un ticket.
        NE suppose pas que les IDs sont fixes -- ils varient par projet Jira.
        """
        import requests
        url = f"{self._base_url}/rest/api/3/issue/{ticket_id}/transitions"
        try:
            response = requests.get(url, auth=self._auth, headers=self._headers(), timeout=10)
        except requests.ConnectionError:
            raise ConnectionError(f"Impossible de joindre Jira ({self._base_url}).")
        except requests.Timeout:
            raise TimeoutError("La requête Jira a dépassé le délai de 10 secondes.")

        if response.status_code == 401:
            raise PermissionError("Authentification Jira invalide.")
        if response.status_code == 404:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")

        response.raise_for_status()
        return response.json().get("transitions", [])

    def apply_transition(self, ticket_id: str, transition_id: str) -> dict:
        """
        Applique une transition Jira par son ID réel récupéré depuis get_transitions.
        Jamais un ID en dur.
        """
        import requests
        url = f"{self._base_url}/rest/api/3/issue/{ticket_id}/transitions"
        body = {"transition": {"id": transition_id}}
        try:
            response = requests.post(url, auth=self._auth, headers=self._headers(), json=body, timeout=10)
        except requests.ConnectionError:
            raise ConnectionError(f"Impossible de joindre Jira ({self._base_url}).")
        except requests.Timeout:
            raise TimeoutError("Timeout lors de l'application de la transition.")

        if response.status_code == 401:
            raise PermissionError("Authentification Jira invalide.")
        if response.status_code == 404:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")
        if response.status_code == 400:
            raise ValueError(f"Transition invalide pour le ticket '{ticket_id}'.")

        response.raise_for_status()
        return {"succes": True, "ticket_id": ticket_id, "transition_id": transition_id}

    def update_status(self, ticket_id: str, status_name: str) -> dict:
        """
        Change le statut d'un ticket par son nom lisible.
        Récupère les transitions disponibles, cherche par nom (insensible à la casse).
        """
        transitions = self.get_transitions(ticket_id)

        if not transitions:
            raise ValueError(
                f"Aucune transition disponible pour le ticket '{ticket_id}'. "
                "Vérifie que tu as les droits nécessaires sur ce ticket."
            )

        status_recherche = status_name.strip().lower()
        transition_trouvee = None
        for t in transitions:
            if t.get("name", "").lower() == status_recherche:
                transition_trouvee = t
                break

        if transition_trouvee is None:
            noms_disponibles = [t.get("name", "") for t in transitions]
            raise ValueError(
                f"Statut '{status_name}' introuvable pour le ticket '{ticket_id}'. "
                f"Statuts disponibles : {', '.join(noms_disponibles)}"
            )

        self.apply_transition(ticket_id, transition_trouvee["id"])
        return {
            "succes": True,
            "ticket_id": ticket_id,
            "nouveau_statut": transition_trouvee["name"],
            "transition_id": transition_trouvee["id"],
    
        }
    def get_attachments(self, ticket_id: str) -> list:
        """
        Retourne la liste des pièces jointes d'un ticket Jira.
        Chaque élément : {id, filename, content_url, mime_type, size}
        """
        import requests
        url = f"{self._base_url}/rest/api/3/issue/{ticket_id}"
        try:
            response = requests.get(
                url, auth=self._auth,
                headers={"Accept": "application/json"},
                timeout=10
            )
        except requests.ConnectionError:
            raise ConnectionError(f"Impossible de joindre Jira ({self._base_url}).")
        except requests.Timeout:
            raise TimeoutError("Timeout Jira.")

        if response.status_code == 401:
            raise PermissionError("Authentification Jira invalide.")
        if response.status_code == 404:
            raise FileNotFoundError(f"Ticket '{ticket_id}' introuvable.")

        response.raise_for_status()
        fields = response.json().get("fields", {})
        attachments = fields.get("attachment", [])

        return [
            {
                "id": a.get("id", ""),
                "filename": a.get("filename", ""),
                "content_url": a.get("content", ""),
                "mime_type": a.get("mimeType", ""),
                "size": a.get("size", 0),
            }
            for a in attachments
        ]

    def download_attachment(self, content_url: str, dest_path: str) -> dict:
        """
        Télécharge une pièce jointe Jira vers dest_path.
        Utilise l'authentification Jira pour accéder au fichier.
        """
        import requests
        from pathlib import Path

        try:
            response = requests.get(
                content_url,
                auth=self._auth,
                timeout=30,
                stream=True,
            )
        except requests.ConnectionError:
            raise ConnectionError("Impossible de télécharger la pièce jointe.")
        except requests.Timeout:
            raise TimeoutError("Timeout lors du téléchargement.")

        if response.status_code == 401:
            raise PermissionError("Authentification invalide pour le téléchargement.")
        if response.status_code == 404:
            raise FileNotFoundError(f"Pièce jointe introuvable : {content_url}")

        response.raise_for_status()

        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        taille = 0
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    taille += len(chunk)

        return {"succes": True, "dest_path": str(dest), "size": taille}  