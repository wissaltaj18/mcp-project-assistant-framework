"""
Implémentation concrète de GitPort : appelle git en ligne de commande via
subprocess. Le token d'authentification (dépôts privés) n'est utilisé
QUE pendant l'appel de clonage -- l'URL du remote est immédiatement
nettoyée après, et tout message d'erreur est assaini, pour que le token
ne soit JAMAIS persisté sur disque ni visible dans un log.
"""

import os
import subprocess
from typing import List, Optional

from core.ports.git_port import GitPort


class LocalGitProvider(GitPort):
    """Interroge un vrai dépôt Git local, comme les commandes git que tu tapes toi-même."""

    def get_current_commit_hash(self, project_root: str) -> "str | None":
        try:
            resultat = subprocess.run(
                ["git", "-C", project_root, "rev-parse", "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
            )
            return resultat.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def get_changed_files_since(self, project_root: str, old_commit_hash: str) -> List[str]:
        try:
            resultat = subprocess.run(
                ["git", "-C", project_root, "diff", "--name-only", old_commit_hash, "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
            )
            fichiers = [f.strip() for f in resultat.stdout.splitlines() if f.strip().endswith(".py")]
            return fichiers
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def clone_repository(self, repo_url: str, destination_path: str, branch: Optional[str] = None, auth_token: Optional[str] = None) -> "str | None":
        url_pour_clone = self._construire_url_authentifiee(repo_url, auth_token)

        commande = ["git", "clone", "--depth", "1"]
        if branch:
            commande += ["--branch", branch]
        commande += [url_pour_clone, destination_path]

        env_sans_prompt = os.environ.copy()
        env_sans_prompt["GIT_TERMINAL_PROMPT"] = "0"

        try:
            resultat = subprocess.run(
                commande,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                env=env_sans_prompt,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return self._nettoyer_message(f"Le clonage de {repo_url} a dépassé le délai autorisé (60s).", auth_token)
        except FileNotFoundError:
            return "Git n'est pas installé ou accessible sur cette machine."

        if auth_token:
            self._nettoyer_url_remote(destination_path, repo_url)

        if resultat.returncode != 0:
            message_erreur = resultat.stderr.strip()[:500] or "Échec du clonage, raison inconnue."
            return self._nettoyer_message(message_erreur, auth_token)

        return None

    def _construire_url_authentifiee(self, repo_url: str, auth_token: Optional[str]) -> str:
        if not auth_token or not repo_url.startswith("https://"):
            return repo_url
        return repo_url.replace("https://", f"https://{auth_token}@", 1)

    def _nettoyer_url_remote(self, destination_path: str, url_propre: str) -> None:
        try:
            subprocess.run(
                ["git", "-C", destination_path, "remote", "set-url", "origin", url_propre],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _nettoyer_message(self, message: str, auth_token: Optional[str]) -> str:
        if auth_token and auth_token in message:
            return message.replace(auth_token, "***")
        return message