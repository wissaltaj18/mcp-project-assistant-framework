"""
Vérifie l'authentification pour dépôts privés (Sprint 17) : le token
n'est jamais persisté sur disque après clone, jamais visible dans un
message d'erreur, et reste toujours optionnel (rétrocompatibilité).
"""

import subprocess

from infra.local_git_provider import LocalGitProvider


def test_injecte_le_token_uniquement_pour_https():
    provider = LocalGitProvider()
    url = provider._construire_url_authentifiee("https://github.com/user/repo.git", "MON_TOKEN")
    assert url == "https://MON_TOKEN@github.com/user/repo.git"


def test_najoute_pas_le_token_pour_une_url_ssh():
    provider = LocalGitProvider()
    url = provider._construire_url_authentifiee("git@github.com:user/repo.git", "MON_TOKEN")
    assert url == "git@github.com:user/repo.git"


def test_sans_token_url_inchangee():
    provider = LocalGitProvider()
    url = provider._construire_url_authentifiee("https://github.com/user/repo.git", None)
    assert url == "https://github.com/user/repo.git"


def test_retire_le_token_dun_message_derreur():
    provider = LocalGitProvider()
    message = provider._nettoyer_message(
        "fatal: could not access https://SECRET123@github.com/user/repo.git/", "SECRET123"
    )
    assert "SECRET123" not in message
    assert "***" in message


def test_le_token_est_reellement_retire_de_git_config_apres_clone(tmp_path):
    depot_source = tmp_path / "source"
    depot_source.mkdir()
    subprocess.run(["git", "init"], cwd=str(depot_source), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "a@a.com"], cwd=str(depot_source), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(depot_source), capture_output=True)
    (depot_source / "fichier.txt").write_text("contenu")
    subprocess.run(["git", "add", "."], cwd=str(depot_source), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(depot_source), capture_output=True, check=True)

    destination = tmp_path / "clone"
    provider = LocalGitProvider()
    erreur = provider.clone_repository(str(depot_source), str(destination), auth_token=None)
    assert erreur is None

    subprocess.run(
        ["git", "-C", str(destination), "remote", "set-url", "origin", "https://VRAI_SECRET@fake.example.com/repo.git"],
        capture_output=True,
    )

    provider._nettoyer_url_remote(str(destination), "https://fake.example.com/repo.git")

    remote_final = subprocess.run(
        ["git", "-C", str(destination), "remote", "get-url", "origin"], capture_output=True, text=True
    ).stdout.strip()
    assert "VRAI_SECRET" not in remote_final
    assert remote_final == "https://fake.example.com/repo.git"


def test_clone_repository_reste_retrocompatible_sans_auth_token(tmp_path):
    depot_source = tmp_path / "source"
    depot_source.mkdir()
    subprocess.run(["git", "init"], cwd=str(depot_source), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "a@a.com"], cwd=str(depot_source), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(depot_source), capture_output=True)
    (depot_source / "fichier.txt").write_text("contenu")
    subprocess.run(["git", "add", "."], cwd=str(depot_source), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(depot_source), capture_output=True, check=True)

    destination = tmp_path / "clone"
    provider = LocalGitProvider()
    erreur = provider.clone_repository(str(depot_source), str(destination))

    assert erreur is None
    assert (destination / "fichier.txt").exists()