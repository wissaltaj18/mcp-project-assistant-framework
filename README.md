# MCP Project Assistant Framework

![CI](https://github.com/wissaltaj18/mcp-project-assistant-framework/actions/workflows/ci.yml/badge.svg)

Framework agentique (Model Context Protocol) qui connecte un LLM à un cycle de développement logiciel complet : lecture de ticket Jira, analyse de code réel, proposition de plan, approbation humaine, exécution, vérification qualité (SonarCloud), commit/push Git, et clôture du ticket — le tout piloté depuis Claude Desktop.

**Principe central :** aucune règle métier n'est codée en dur dans le framework — tout vit dans une Knowledge Base générée par analyse statique du dépôt cible (`workspaces/{id}/resources/*.md`). Changer de projet = cloner un nouveau dépôt, jamais modifier le code du framework.

**Preuve du Dependency Inversion Principle :** le framework supporte plusieurs LLM interchangeables (Qwen local via Ollama, Gemini via API) — basculer de l'un à l'autre ne demande de changer qu'une variable d'environnement (`ACTIVE_LLM_PROVIDER`), aucune modification de `core/`, `services/`, ni `agents/`.

---

## État d'avancement (mise à jour au 25/08/2026)

- ✅ Core (entities, value objects, ports) — testé
- ✅ Système Workspace : clone, activation, génération automatique de Knowledge Base par analyse statique du dépôt
- ✅ Indexation vectorielle (RAG) incrémentale du code source
- ✅ Système `create_plan` → approbation humaine → `approve_plan` : aucune modification de code sans validation explicite
- ✅ Exécution réelle de plans : `modify_file`, `create_file`, `database_write`, `git_push`, `create_pull_request`
- ✅ Intégration Jira Cloud v3 complète : lecture ticket, changement de statut via transitions réelles, commentaires, téléchargement de pièces jointes
- ✅ Intégration SonarCloud : lecture du Quality Gate et des métriques (bugs, vulnérabilités, couverture)
- ✅ Intégration Git sécurisée : `sync_workspace` (pull sans jamais de reset --hard), `git_push` automatisé avec détection des fichiers modifiés
- ✅ Workflow Jira de bout en bout (`jira_workflow`) : ticket → plan → approbation → tests → push → Quality Gate → clôture conditionnelle
- ✅ 11 Prompts MCP opérationnels : `jira_workflow`, `implement_feature`, `review_code`, `fix_bug`, `security_review`, `refactor`, `explain_architecture`, `onboard_project`, etc.
- ✅ 27 Tools MCP exposés (Workspace, lecture/analyse de code, Plan/Approbation, Jira, SonarCloud, Git)
- ✅ 414+ tests automatisés (pytest), tous passants
- ✅ CI/CD GitHub Actions sur le framework lui-même (tests + lint à chaque push)
- ⏳ Lecture du statut des pipelines GitHub Actions (Agentic CI Watcher) — roadmap
- ⏳ Boucle de correction automatique après échec CI — roadmap

---

## Architecture

```
Ticket Jira
  → lecture (read_jira_ticket)
  → statut "En cours" (update_jira_status)
  → téléchargement pièces jointes si présentes (download_jira_attachment)
  → vérification anti-duplication (check_existing_feature)
  → chargement Knowledge Base du Workspace
  → proposition de plan (create_plan) — jamais exécuté automatiquement
  → approbation humaine explicite
  → exécution (approve_plan) : modification/création de fichier, écriture vérifiée par relecture disque
  → tests automatiques (pytest / PHPUnit selon le langage détecté)
  → commit + push Git (après confirmation humaine)
  → lecture Quality Gate SonarCloud
  → commentaire de synthèse sur le ticket
  → clôture conditionnelle : "Terminé" uniquement si Quality Gate PASS
```

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt
```

### Configuration (.env)

```env
# LLM actif
ACTIVE_LLM_PROVIDER=gemini
GEMINI_API_KEY=ta-cle-gemini

# Jira (optionnel)
JIRA_BASE_URL=https://ton-org.atlassian.net
JIRA_EMAIL=ton-email@example.com
JIRA_API_TOKEN=ton-token-jira

# SonarCloud (optionnel)
SONAR_TOKEN=ton-token-sonarcloud
SONAR_ORGANIZATION=ton-organisation
SONAR_PROJECT_KEY=ton-projet-sonarcloud
```

---

## Connexion à Claude Desktop

Ajoute cette entrée dans `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "mcp-project-assistant": {
      "command": "CHEMIN_VERS\\.venv\\Scripts\\python.exe",
      "args": ["CHEMIN_VERS\\server.py"],
      "env": {
        "GEMINI_API_KEY": "ta-cle-gemini"
      }
    }
  }
}
```

---

## Lancer les tests

```bash
python -m pytest tests/ -v
```
→ 414+ tests, exécutés en quelques secondes.

## CI/CD

Chaque push sur `main` déclenche automatiquement :
- l'exécution complète de la suite de tests (`.github/workflows/ci.yml`)
- un lint du code avec `ruff`

---

## Utilisation typique depuis Claude Desktop

### 1. Créer et préparer un Workspace

```
Prépare le Workspace à partir de https://github.com/mon-org/mon-projet.git
```

Le tool `prepare_workspace` enchaîne automatiquement : clone → activation → génération de la Knowledge Base par analyse statique → indexation vectorielle.

### 2. Traiter un ticket Jira de bout en bout

```
jira_workflow mon-workspace KAN-42
```

L'agent lit le ticket, propose un plan, attend ton approbation, exécute, lance les tests, vérifie SonarCloud, et clôture le ticket si tout est vert.

### 3. Implémenter une fonctionnalité sans ticket Jira

```
implement_feature mon-workspace "Ajouter un bouton de tri par prix"
```

### 4. Review de code

```
review_code mon-workspace src/Controller/ProductController.php
```

---

## Tools MCP principaux

| Tool | Rôle |
|---|---|
| `prepare_workspace` | Clone, active, analyse et indexe un dépôt Git |
| `create_plan` / `approve_plan` / `reject_plan` | Cycle de modification avec approbation humaine obligatoire |
| `read_jira_ticket` / `update_jira_status` / `add_jira_comment` | Intégration Jira |
| `download_jira_attachment` | Télécharge une pièce jointe Jira dans le Workspace |
| `get_sonar_report` | Lecture du Quality Gate SonarCloud |
| `sync_workspace` / `get_git_diff` | Synchronisation Git sécurisée |
| `run_tests` | Exécute la suite de tests réelle du Workspace (pytest ou PHPUnit) |
| `check_existing_feature` | Anti-duplication avant toute proposition de code |

---

## Philosophie de sécurité

- **Aucune modification de code sans approbation humaine explicite** — `create_plan` ne peut jamais s'auto-approuver.
- **Aucun `git reset --hard`** — `sync_workspace` refuse de synchroniser si des modifications locales non commitées existent.
- **Preuve réelle à chaque étape** — chaque exécution est vérifiée par relecture du fichier depuis le disque, jamais un succès déclaratif.
- **Clôture Jira conditionnelle** — un ticket ne passe "Terminé" que si le Quality Gate SonarCloud est PASS.