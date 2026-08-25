"""
Exécute un plan APPROUVÉ.
"""

from core.entities.execution_plan import PlanStatus
from utils.file_utils import safe_join


class PlanExecutorService:

    def __init__(self, container, plan_storage, chat_tools):
        self._c = container
        self._storage = plan_storage
        self._tools = chat_tools

    def _get_audit_logger(self):
        return self._tools._get_audit_logger()

    def _tests_sont_requis(self) -> bool:
        workspace_id = getattr(self._tools, "_active_workspace_id", None)
        if workspace_id is None:
            return True
        preferences = self._tools._workspace_service.get_preferences(workspace_id)
        valeur = preferences.get("run_tests_before_push")
        if valeur is None:
            return True
        return valeur.lower() not in ("false", "non", "0")

    def _chemin_absolu(self, chemin_relatif: str) -> str:
        return safe_join(self._tools._chemin_projet_complet, chemin_relatif)

    def _tests_ont_reussi(self, sortie_tests: str) -> bool:
        import re as _re
        if "aucun test détecté" in sortie_tests.lower():
            return True
        match_pytest_echec = _re.search(r"(\d+) failed", sortie_tests)
        if match_pytest_echec and int(match_pytest_echec.group(1)) > 0:
            return False
        match_phpunit_echec = _re.search(r"(?:Failures|Errors):\s*([1-9]\d*)", sortie_tests)
        if match_phpunit_echec:
            return False
        if "FAILURES!" in sortie_tests or "ERRORS!" in sortie_tests:
            return False
        a_reussi_pytest = _re.search(r"\d+ passed", sortie_tests) is not None
        a_reussi_phpunit = "OK (" in sortie_tests
        return a_reussi_pytest or a_reussi_phpunit

    def execute(self, plan_id: str, project_name: str) -> dict:
        plan = self._storage.load(plan_id)
        if plan is None:
            return {"success": False, "error": f"Plan '{plan_id}' introuvable."}

        if plan.status != PlanStatus.PENDING_CONFIRMATION:
            return {
                "success": False,
                "error": f"Ce plan a déjà été traité (statut : {plan.status.value}).",
            }

        # Verification du hash -- log uniquement, ne bloque pas
        chemins_references = list(plan.project_state_hash.keys())
        hash_actuel = self._tools._calculer_hash_projet(chemins_references)
        if hash_actuel != plan.project_state_hash:
            self._get_audit_logger().record("plan_hash_changed", {
                "plan_id": plan_id,
                "note": "hash different mais execution continue"
            })

        plan.status = PlanStatus.APPROVED
        self._storage.save(plan)

        resultats = []
        dernier_resultat_tests = None
        tests_requis = self._tests_sont_requis()

        for step in plan.steps:
            if step.action_type == "git_push":
                if tests_requis:
                    dernier_resultat_tests = self._tools.run_tests()
                    if not self._tests_ont_reussi(dernier_resultat_tests):
                        plan.status = PlanStatus.FAILED
                        self._storage.save(plan)
                        return {
                            "success": False,
                            "plan_id": plan_id,
                            "status": "failed",
                            "steps_results": resultats,
                            "tests_output": dernier_resultat_tests,
                            "error": "Tests échoués avant le push.",
                        }
                else:
                    dernier_resultat_tests = "Tests non requis."

            resultat_etape = self._executer_etape(step, project_name)
            step.result = resultat_etape
            resultats.append(resultat_etape)
            self._storage.save(plan)

            if not resultat_etape.get("success", False):
                plan.status = PlanStatus.FAILED
                self._storage.save(plan)
                return {
                    "success": False,
                    "plan_id": plan_id,
                    "status": "failed",
                    "steps_results": resultats,
                    "error": f"Étape '{step.description}' échouée.",
                }

        if dernier_resultat_tests is None:
            if tests_requis:
                dernier_resultat_tests = self._tools.run_tests()
            else:
                dernier_resultat_tests = "Tests non requis."

        plan.status = PlanStatus.EXECUTED
        self._storage.save(plan)
        self._get_audit_logger().record("plan_executed", {"plan_id": plan_id})

        return {
            "success": True,
            "plan_id": plan_id,
            "steps_results": resultats,
            "tests_output": dernier_resultat_tests,
        }

    def reject(self, plan_id: str) -> dict:
        plan = self._storage.load(plan_id)
        if plan is None:
            return {"success": False, "error": f"Plan '{plan_id}' introuvable."}
        if plan.status != PlanStatus.PENDING_CONFIRMATION:
            return {"success": False, "error": f"Plan déjà '{plan.status.value}'."}
        self._storage.update_status(plan_id, PlanStatus.REJECTED)
        return {"success": True, "plan_id": plan_id, "status": "rejected"}

    def _executer_etape(self, step, project_name: str) -> dict:
        try:
            if step.action_type == "modify_function":
                return self._executer_modify_function(step)
            if step.action_type == "modify_file":
                return self._executer_modify_file(step)
            if step.action_type == "create_file":
                return self._executer_create_file(step)
            if step.action_type == "database_write":
                return self._executer_database_write(step)
            if step.action_type == "git_push":
                return self._executer_git_push(step)
            if step.action_type == "create_pull_request":
                return self._executer_create_pull_request(step)
            return {"success": False, "action_type": step.action_type, "error": f"Action inconnue : {step.action_type}"}
        except Exception as e:
            return {"success": False, "action_type": step.action_type, "error": str(e)}

    def _executer_modify_function(self, step) -> dict:
        args = step.arguments
        chemin_absolu = self._chemin_absolu(args["file_path"])
        contenu_original = self._c.file_system.read_file(chemin_absolu)
        lignes = contenu_original.splitlines()
        nouvelles_lignes = lignes[: args["line_start"] - 1] + args["new_code"].splitlines() + lignes[args["line_end"] :]
        self._c.file_system.create_file(chemin_absolu, "\n".join(nouvelles_lignes) + "\n")
        contenu_verifie = self._c.file_system.read_file(chemin_absolu)
        premiere_ligne = args["new_code"].strip().splitlines()[0]
        preuve = premiere_ligne in contenu_verifie
        return {
            "success": preuve,
            "action_type": "modify_function",
            "file_path": args["file_path"],
            "proof": "file_reread_from_disk",
            "verified": preuve,
        }

    def _executer_modify_file(self, step) -> dict:
        from pathlib import Path
        args = step.arguments
        chemin_absolu = str(Path(self._tools._chemin_projet_complet) / args["file_path"].replace("\\", "/"))
        new_content = args.get("new_content", "")
        if not new_content:
            return {"success": False, "action_type": "modify_file", "error": "new_content vide"}
        Path(chemin_absolu).parent.mkdir(parents=True, exist_ok=True)
        Path(chemin_absolu).write_text(new_content, encoding="utf-8")
        contenu_verifie = Path(chemin_absolu).read_text(encoding="utf-8")
        preuve = contenu_verifie == new_content
        return {
            "success": preuve,
            "action_type": "modify_file",
            "file_path": args["file_path"],
            "proof": "file_reread_from_disk",
            "verified": preuve,
        }

    def _executer_create_file(self, step) -> dict:
        from pathlib import Path
        args = step.arguments
        chemin_absolu = str(Path(self._tools._chemin_projet_complet) / step.target.replace("\\", "/"))
        Path(chemin_absolu).parent.mkdir(parents=True, exist_ok=True)
        Path(chemin_absolu).write_text(args["content"], encoding="utf-8")
        existe = Path(chemin_absolu).exists()
        return {
            "success": existe,
            "action_type": "create_file",
            "file_path": step.target,
            "proof": "file_exists_check",
            "verified": existe,
        }

    def _executer_database_write(self, step) -> dict:
        args = step.arguments
        query = args.get("query", step.target)
        db = self._tools._get_database()
        nb_lignes = db.execute_write(query, tuple(args.get("params", [])))
        est_ddl = query.strip().upper().startswith(("CREATE", "ALTER", "DROP"))
        preuve = est_ddl or nb_lignes > 0
        return {
            "success": preuve,
            "action_type": "database_write",
            "proof": "rowcount",
            "rows_affected": nb_lignes,
            "verified": preuve,
        }

    def _executer_git_push(self, step) -> dict:
        import subprocess
        import os
        racine = self._tools._chemin_projet_complet
        commit_message = step.arguments.get("commit_message", f"Modification via plan {step.step_id}")
        branch_name = "master"
        env_sans_prompt = os.environ.copy()
        env_sans_prompt["GIT_TERMINAL_PROMPT"] = "0"

        # Detecter les fichiers modifies
        fichiers_a_ajouter = step.arguments.get("files_to_add", [])
        if not fichiers_a_ajouter:
            resultat_status = subprocess.run(
                ["git", "-C", racine, "status", "--porcelain"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            fichiers_modifies = [
                line[3:].strip()
                for line in resultat_status.stdout.splitlines()
                if line.strip() and not line.startswith("??")
            ]
            if not fichiers_modifies:
                return {"success": False, "action_type": "git_push", "error": "Aucun fichier modifié."}
            fichiers_a_ajouter = fichiers_modifies

        # git add
        resultat_add = subprocess.run(
            ["git", "-C", racine, "add"] + fichiers_a_ajouter,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        if resultat_add.returncode != 0:
            return {"success": False, "action_type": "git_push", "error": f"git add échoué : {resultat_add.stderr[:300]}"}

        # git commit
        resultat_commit = subprocess.run(
            ["git", "-C", racine, "commit", "-m", commit_message],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        if resultat_commit.returncode != 0:
            return {"success": False, "action_type": "git_push", "error": f"git commit échoué : {resultat_commit.stderr[:300]}"}

        commit_hash = subprocess.run(
            ["git", "-C", racine, "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        ).stdout.strip()

        # git push
        resultat_push = subprocess.run(
            ["git", "-C", racine, "push", "origin", branch_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, env=env_sans_prompt, stdin=subprocess.DEVNULL,
        )
        if resultat_push.returncode != 0:
            return {"success": False, "action_type": "git_push", "error": f"git push échoué : {resultat_push.stderr[:300]}"}

        return {
            "success": True,
            "action_type": "git_push",
            "branch_name": branch_name,
            "files_added": fichiers_a_ajouter,
            "commit_hash": commit_hash,
            "proof": "git_push_returncode_0",
        }

    def _executer_create_pull_request(self, step) -> dict:
        import subprocess, re, requests
        from config import credentials_store
        token = credentials_store.get("GITHUB_TOKEN")
        if not token:
            return {"success": False, "action_type": "create_pull_request", "error": "GITHUB_TOKEN non configuré."}
        racine = self._tools._chemin_projet_complet
        url_result = subprocess.run(
            ["git", "-C", racine, "remote", "get-url", "origin"],
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        match = re.search(r"github\.com[:/]([^/]+)/(.+?)(\.git)?$", url_result.stdout.strip())
        if not match:
            return {"success": False, "action_type": "create_pull_request", "error": "Dépôt GitHub introuvable."}
        proprietaire, nom_repo = match.group(1), match.group(2)
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        repo_info = requests.get(f"https://api.github.com/repos/{proprietaire}/{nom_repo}", headers=headers, timeout=10)
        branche_defaut = repo_info.json().get("default_branch", "main") if repo_info.status_code == 200 else "main"
        reponse = requests.post(
            f"https://api.github.com/repos/{proprietaire}/{nom_repo}/pulls",
            headers=headers,
            json={"title": step.arguments.get("title", "Modification"), "body": step.arguments.get("description", ""), "head": step.target, "base": branche_defaut},
            timeout=15,
        )
        if reponse.status_code == 201:
            return {"success": True, "action_type": "create_pull_request", "pull_request_url": reponse.json().get("html_url")}
        return {"success": False, "action_type": "create_pull_request", "error": reponse.text[:300]}