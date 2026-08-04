"""
Exécute un plan APPROUVÉ -- jamais appelé par le LLM, uniquement par
l'endpoint /approve du backend, déclenché par un clic utilisateur.
Vérifie la cohérence du projet avant d'exécuter, s'arrête à la première
étape en échec (jamais de faux succès), et renvoie une PREUVE RÉELLE et
vérifiable pour chaque étape. Chaque décision est journalisée (audit).

Résolution de chemin : une SEULE source de vérité (self._tools._chemin_projet_complet).
"""

from core.entities.execution_plan import PlanStatus
from utils.file_utils import safe_join


class PlanExecutorService:
    """Cas d'usage : vérifier, exécuter, et prouver le résultat d'un plan approuvé."""

    def __init__(self, container, plan_storage, chat_tools):
        self._c = container
        self._storage = plan_storage
        self._tools = chat_tools

    def _get_audit_logger(self):
        return self._tools._get_audit_logger()

    def _tests_sont_requis(self) -> bool:
        """
        Lit la préférence 'run_tests_before_push' du Workspace actif, si
        présente -- comportement par défaut (tests toujours requis)
        inchangé si aucune préférence n'est définie ou si aucun
        Workspace n'est actif (rétrocompatibilité totale).
        """
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
        """
        Détermine si la sortie de run_tests() indique un VRAI succès --
        couvre pytest et PHPUnit. Volontairement STRICT : exige une preuve
        explicite de succès, plutôt que de se contenter de l'absence de
        mots d'échec -- une erreur d'environnement ne compte JAMAIS comme succès.
        """
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
                "error": f"Ce plan a déjà été traité (statut actuel : {plan.status.value}). Impossible de le rejouer.",
            }

        chemins_references = list(plan.project_state_hash.keys())
        hash_actuel = self._tools._calculer_hash_projet(chemins_references)
        if hash_actuel != plan.project_state_hash:
            self._storage.update_status(plan_id, PlanStatus.INVALIDATED)
            self._get_audit_logger().record("plan_invalidated", {"plan_id": plan_id})
            return {
                "success": False,
                "status": "invalidated",
                "error": "Le projet a changé depuis la création de ce plan. Exécution refusée pour sécurité. Recrée un nouveau plan.",
                "hash_avant": plan.project_state_hash,
                "hash_maintenant": hash_actuel,
            }

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
                        self._get_audit_logger().record("plan_failed", {"plan_id": plan_id, "reason": "tests_failed_before_push"})
                        return {
                            "success": False,
                            "plan_id": plan_id,
                            "status": "failed",
                            "steps_results": resultats,
                            "tests_output": dernier_resultat_tests,
                            "error": "Les tests ont échoué avant le push -- aucun commit ni push n'a été effectué.",
                        }
                else:
                    dernier_resultat_tests = "Tests non exigés pour ce Workspace (préférence utilisateur : run_tests_before_push=false)."

            resultat_etape = self._executer_etape(step, project_name)
            step.result = resultat_etape
            resultats.append(resultat_etape)
            self._storage.save(plan)

            if not resultat_etape.get("success", False):
                plan.status = PlanStatus.FAILED
                self._storage.save(plan)
                self._get_audit_logger().record("plan_failed", {"plan_id": plan_id, "reason": f"step_failed:{step.action_type}"})
                return {
                    "success": False,
                    "plan_id": plan_id,
                    "status": "failed",
                    "steps_results": resultats,
                    "error": (
                        f"L'étape '{step.description}' a échoué (voir steps_results). "
                        f"Exécution arrêtée -- les étapes suivantes n'ont PAS été exécutées."
                    ),
                }

        if dernier_resultat_tests is None:
            if tests_requis:
                dernier_resultat_tests = self._tools.run_tests()
            else:
                dernier_resultat_tests = "Tests non exigés pour ce Workspace (préférence utilisateur : run_tests_before_push=false)."

        plan.status = PlanStatus.EXECUTED
        self._storage.save(plan)
        self._get_audit_logger().record("plan_executed", {"plan_id": plan_id, "nb_steps": len(resultats)})

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
            return {"success": False, "error": f"Ce plan est déjà '{plan.status.value}', impossible de le rejeter maintenant."}
        self._storage.update_status(plan_id, PlanStatus.REJECTED)
        self._get_audit_logger().record("plan_rejected", {"plan_id": plan_id})
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
            return {"success": False, "action_type": step.action_type, "error": f"Type d'action inconnu : {step.action_type}"}
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
        premiere_ligne_attendue = args["new_code"].strip().splitlines()[0]
        preuve_confirmee = premiere_ligne_attendue in contenu_verifie

        return {
            "success": preuve_confirmee,
            "action_type": "modify_function",
            "file_path": args["file_path"],
            "proof": "file_reread_from_disk",
            "verified": preuve_confirmee,
            "diff": f"--- AVANT ---\n{args['original_code']}\n\n--- APRÈS ---\n{args['new_code']}",
        }

    def _executer_modify_file(self, step) -> dict:
        args = step.arguments
        chemin_absolu = self._chemin_absolu(args["file_path"])
        self._c.file_system.create_file(chemin_absolu, args["new_content"])

        contenu_verifie = self._c.file_system.read_file(chemin_absolu)
        preuve_confirmee = contenu_verifie == args["new_content"]

        return {
            "success": preuve_confirmee,
            "action_type": "modify_file",
            "file_path": args["file_path"],
            "proof": "file_reread_from_disk",
            "verified": preuve_confirmee,
        }

    def _executer_create_file(self, step) -> dict:
        args = step.arguments
        chemin_absolu = self._chemin_absolu(step.target)
        self._c.file_system.create_file(chemin_absolu, args["content"])

        fichier_existe_vraiment = self._c.file_system.file_exists(chemin_absolu)

        return {
            "success": fichier_existe_vraiment,
            "action_type": "create_file",
            "file_path": step.target,
            "proof": "file_exists_check",
            "verified": fichier_existe_vraiment,
        }

    def _executer_database_write(self, step) -> dict:
        args = step.arguments
        query = args.get("query", step.target)
        db = self._tools._get_database()
        nb_lignes = db.execute_write(query, tuple(args.get("params", [])))

        est_ddl = query.strip().upper().startswith(("CREATE", "ALTER", "DROP"))
        preuve_confirmee = est_ddl or nb_lignes > 0

        return {
            "success": preuve_confirmee,
            "action_type": "database_write",
            "proof": "rowcount_returned_by_sqlite",
            "rows_affected": nb_lignes,
            "verified": preuve_confirmee,
        }

    def _executer_git_push(self, step) -> dict:
        import subprocess
        import os
        racine = self._tools._chemin_projet_complet
        branch_name = step.target
        commit_message = step.arguments.get("commit_message", f"Modification via plan {step.step_id}")

        fichiers_a_ajouter = step.arguments.get("files_to_add", [])
        if not fichiers_a_ajouter:
            return {
                "success": False, "action_type": "git_push",
                "error": "Aucun fichier connu à committer pour cette étape -- push refusé par sécurité.",
            }

        resultat_checkout = subprocess.run(
            ["git", "-C", racine, "checkout", "-b", branch_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        if resultat_checkout.returncode != 0:
            resultat_checkout = subprocess.run(
                ["git", "-C", racine, "checkout", branch_name],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            if resultat_checkout.returncode != 0:
                return {"success": False, "action_type": "git_push", "error": f"Impossible de créer/basculer sur la branche : {resultat_checkout.stderr[:300]}"}

        resultat_add = subprocess.run(["git", "-C", racine, "add"] + fichiers_a_ajouter,
                                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        if resultat_add.returncode != 0:
            return {"success": False, "action_type": "git_push", "error": f"git add a échoué : {resultat_add.stderr[:300]}"}

        resultat_commit = subprocess.run(["git", "-C", racine, "commit", "-m", commit_message],
                                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        if resultat_commit.returncode != 0:
            return {
                "success": False, "action_type": "git_push",
                "error": f"git commit a échoué : {resultat_commit.stdout[:300]}{resultat_commit.stderr[:300]}",
            }

        resultat_hash = subprocess.run(["git", "-C", racine, "rev-parse", "HEAD"],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        commit_hash_reel = resultat_hash.stdout.strip()

        env_sans_prompt = os.environ.copy()
        env_sans_prompt["GIT_TERMINAL_PROMPT"] = "0"

        resultat_push = subprocess.run(["git", "-C", racine, "push", "-u", "origin", branch_name],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                                        env=env_sans_prompt, stdin=subprocess.DEVNULL)

        resultat_verif_remote = subprocess.run(["git", "-C", racine, "ls-remote", "--heads", "origin", branch_name],
                                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        branche_confirmee_sur_remote = branch_name in resultat_verif_remote.stdout

        succes_reel = resultat_push.returncode == 0 and branche_confirmee_sur_remote
        if not succes_reel:
            return {
                "success": False, "action_type": "git_push",
                "error": f"Push ou vérification remote a échoué : {resultat_push.stderr[:300]}",
                "commit_hash": commit_hash_reel,
            }

        return {
            "success": True,
            "action_type": "git_push",
            "branch_name": branch_name,
            "files_added": fichiers_a_ajouter,
            "commit_hash": commit_hash_reel,
            "proof": "git_ls_remote_verification",
            "verified_on_remote": branche_confirmee_sur_remote,
        }

    def _executer_create_pull_request(self, step) -> dict:
        import subprocess
        import re
        import requests
        from config import credentials_store

        token = credentials_store.get("GITHUB_TOKEN")
        if not token:
            return {"success": False, "action_type": "create_pull_request", "error": "GITHUB_TOKEN non configuré."}

        racine = self._tools._chemin_projet_complet
        resultat_url = subprocess.run(["git", "-C", racine, "remote", "get-url", "origin"],
                                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        match = re.search(r"github\.com[:/]([^/]+)/(.+?)(\.git)?$", resultat_url.stdout.strip())
        if not match:
            return {"success": False, "action_type": "create_pull_request", "error": "Dépôt GitHub introuvable via origin."}
        proprietaire, nom_repo = match.group(1), match.group(2)

        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

        reponse_repo = requests.get(
            f"https://api.github.com/repos/{proprietaire}/{nom_repo}", headers=headers, timeout=10,
        )
        if reponse_repo.status_code != 200:
            return {
                "success": False, "action_type": "create_pull_request",
                "error": f"Impossible de déterminer la branche par défaut du dépôt (code {reponse_repo.status_code}).",
            }
        branche_par_defaut = reponse_repo.json().get("default_branch", "main")

        reponse = requests.post(
            f"https://api.github.com/repos/{proprietaire}/{nom_repo}/pulls",
            headers=headers,
            json={
                "title": step.arguments.get("title", "Modification automatique"),
                "body": step.arguments.get("description", ""),
                "head": step.target,
                "base": branche_par_defaut,
            },
            timeout=15,
        )

        if reponse.status_code == 201:
            donnees = reponse.json()
            return {
                "success": True,
                "action_type": "create_pull_request",
                "proof": "github_api_response",
                "pull_request_url": donnees.get("html_url"),
                "pull_request_number": donnees.get("number"),
            }
        return {"success": False, "action_type": "create_pull_request", "error": reponse.text[:300]}