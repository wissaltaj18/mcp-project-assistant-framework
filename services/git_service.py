"""
Sprint 32 -- GitService : synchronisation Git automatique securisee.
Regles de securite :
  - git pull jamais si working tree dirty
  - git reset --hard jamais
  - git push jamais sans confirmation humaine explicite
"""

import subprocess
from pathlib import Path
from typing import Optional


class GitService:
    """
    Encapsule les operations Git sur un repo local.
    Toutes les operations sont deterministes et sans effet de bord non controle.
    """

    def __init__(self, repo_path: str):
        self._repo_path = str(Path(repo_path).resolve())

    def _run(self, args: list, timeout: int = 30) -> tuple:
        try:
            result = subprocess.run(
                ["git", "-C", self._repo_path] + args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"La commande git a depasse le delai de {timeout} secondes.")
        except FileNotFoundError:
            raise EnvironmentError("Git n'est pas installe ou accessible sur cette machine.")

    def is_git_repo(self) -> bool:
        code, _, _ = self._run(["rev-parse", "--is-inside-work-tree"])
        return code == 0

    def get_status(self) -> dict:
        code, stdout, stderr = self._run(["status", "--porcelain"])
        if code != 0:
            raise RuntimeError(f"git status a echoue : {stderr}")

        modified = []
        untracked = []
        staged = []

        for line in stdout.splitlines():
            if len(line) < 3:
                continue
            xy = line[:2]
            fichier = line[3:].strip()
            if xy[0] in ("M", "A", "D", "R", "C"):
                staged.append(fichier)
            if xy[1] in ("M", "D"):
                modified.append(fichier)
            if xy == "??":
                untracked.append(fichier)

        return {
            "is_clean": not stdout.strip(),
            "modified": modified,
            "untracked": untracked,
            "staged": staged,
        }

    def pull(self, remote: str = "origin", branch: str = "master") -> dict:
        status = self.get_status()

        if not status["is_clean"]:
            fichiers = status["modified"] + status["staged"]
            raise RuntimeError(
                f"Impossible de faire git pull : des modifications locales non committees existent.\n"
                f"Fichiers concernes : {', '.join(fichiers) if fichiers else 'voir git status'}.\n"
                f"Committez ou stashez ces modifications avant de synchroniser."
            )

        code, stdout, stderr = self._run(["pull", remote, branch], timeout=60)
        if code != 0:
            raise RuntimeError(f"git pull a echoue : {stderr}")

        fichiers_maj = []
        for line in stdout.splitlines():
            line = line.strip()
            if "|" in line and not line.startswith("---") and not line.startswith("+++"):
                fichier = line.split("|")[0].strip()
                if fichier:
                    fichiers_maj.append(fichier)

        deja_a_jour = "Already up to date" in stdout or "Deja a jour" in stdout

        return {
            "succes": True,
            "message": stdout,
            "deja_a_jour": deja_a_jour,
            "fichiers_mis_a_jour": fichiers_maj,
        }

    def get_diff_summary(self, depuis: str = "HEAD~1", jusqua: str = "HEAD") -> dict:
        code, stdout, stderr = self._run(["diff", "--name-status", depuis, jusqua])
        if code != 0:
            code2, stdout2, _ = self._run(["diff", "--name-status", "--cached"])
            if code2 != 0:
                return {"fichiers": [], "resume": "Aucune modification detectee."}
            stdout = stdout2

        fichiers = []
        for line in stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                statut_map = {"M": "modifie", "A": "ajoute", "D": "supprime", "R": "renomme"}
                statut = statut_map.get(parts[0][0], parts[0])
                fichiers.append({"statut": statut, "fichier": parts[-1]})

        resume = "\n".join(
            f"- {f['fichier']} ({f['statut']})" for f in fichiers
        ) if fichiers else "Aucune modification detectee."

        return {"fichiers": fichiers, "resume": resume}

    def get_last_commit_hash(self) -> Optional[str]:
        code, stdout, _ = self._run(["rev-parse", "HEAD"])
        return stdout if code == 0 else None

    def get_remote_url(self) -> Optional[str]:
        code, stdout, _ = self._run(["remote", "get-url", "origin"])
        return stdout if code == 0 else None