# """Implémentation concrète de GitPort : appelle git en ligne de commande via subprocess."""

# import subprocess
# from typing import List

# from core.ports.git_port import GitPort


# class LocalGitProvider(GitPort):
#     """Interroge un vrai dépôt Git local, comme les commandes git que tu tapes toi-même."""

#     def get_current_commit_hash(self, project_root: str) -> "str | None":
#         try:
#             resultat = subprocess.run(
#                 ["git", "-C", project_root, "rev-parse", "HEAD"],
#                 capture_output=True, text=True, check=True,
#             )
#             return resultat.stdout.strip()
#         except (subprocess.CalledProcessError, FileNotFoundError):
#             return None

#     def get_changed_files_since(self, project_root: str, old_commit_hash: str) -> List[str]:
#         try:
#             resultat = subprocess.run(
#                 ["git", "-C", project_root, "diff", "--name-only", old_commit_hash, "HEAD"],
#                 capture_output=True, text=True, check=True,
#             )
#             fichiers = [f.strip() for f in resultat.stdout.splitlines() if f.strip().endswith(".py")]
#             return fichiers
#         except (subprocess.CalledProcessError, FileNotFoundError):
#             return []

"""Implémentation concrète de GitPort : appelle git en ligne de commande via subprocess."""

import subprocess
from typing import List

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
    def clone_repository(self, repo_url: str, destination_path: str, branch: "str | None" = None) -> "str | None":
        commande = ["git", "clone", "--depth", "1"]
        if branch:
            commande += ["--branch", branch]
        commande += [repo_url, destination_path]

        try:
            resultat = subprocess.run(
                commande,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
        except subprocess.TimeoutExpired:
            return f"Le clonage de {repo_url} a dépassé le délai autorisé (60s)."
        except FileNotFoundError:
            return "Git n'est pas installé ou accessible sur cette machine."

        if resultat.returncode != 0:
            return resultat.stderr.strip()[:500] or "Échec du clonage, raison inconnue."

        return None