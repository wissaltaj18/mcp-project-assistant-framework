**Principe central :** aucune règle métier n'est codée en dur dans le framework — tout vit dans les fichiers `.md` de `generated_projects/{projet}/resources/`. Changer de projet = changer ces fichiers, jamais le code du framework.

**Preuve du Dependency Inversion Principle :** le framework supporte déjà 2 LLM interchangeables (Qwen local via Ollama, Gemini via API) — basculer de l'un à l'autre ne demande de changer qu'une variable d'environnement (`ACTIVE_LLM_PROVIDER`), aucune modification de `core/`, `services/`, ni `agents/`.

---

## État d'avancement (mise à jour au 18/07/2026)

- ✅ Core (entities, value objects, ports) — testé
- ✅ Lecture réelle de Resources .md — testée
- ✅ Chaîne Prompt → LLM → Résultat — testée
- ✅ Serveur MCP avec 4 tools fonctionnels — testé via inspecteur MCP officiel
- ✅ Deux LLM interchangeables : Qwen local (Ollama) et Gemini (API cloud)
- ✅ Écriture réelle de fichiers sur disque (`create_file`)
- ✅ 3 Prompts opérationnels : `generate_login`, `generate_dashboard`, `generate_navbar`
- ✅ 3 Resources pour AegisAI : `business_rules.md`, `project_context.md`, `coding_guidelines.md`
- ✅ Consigne de rendu HTML autonome, stricte (interdiction d'imports externes)
- ✅ 24 tests automatisés (pytest), tous passants
- ⏳ Prompts supplémentaires (backend, tests, documentation)
- ⏳ Interface visuelle (React) — prévue une fois le cœur du framework stabilisé

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
pip install mcp requests pytest google-genai
```

### Option A — LLM local (Qwen via Ollama)
```bash
ollama pull qwen2.5-coder:1.5b
```

### Option B — LLM cloud (Gemini, gratuit)
Récupérer une clé sur `aistudio.google.com/apikey`.

---

## Lancer les tests

```bash
python -m pytest tests/ -v
```
→ 24 tests, exécutés en moins d'une seconde.

---

## Lancer le serveur MCP

**Avec Qwen local :**
```bash
$env:ACTIVE_LLM_PROVIDER = "ollama_qwen"
$env:OLLAMA_MODEL = "qwen2.5-coder:1.5b"
python server.py
```

**Avec Gemini :**
```bash
$env:ACTIVE_LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "ta-clé"
python server.py
```

Pour tester avec l'inspecteur officiel :
```bash
$env:DANGEROUSLY_OMIT_AUTH = "true"
npx @modelcontextprotocol/inspector python server.py
```

### Tools disponibles
- `read_project_resource(project_name, resource_name)` — lit une Resource
- `list_project_resources(project_name)` — liste les Resources d'un projet
- `list_available_prompts()` — liste les Prompts disponibles
- `generate_feature(project_name, prompt_name, page_name, output_path)` — génère du code et l'écrit sur disque

---

## Lancer la démo "vibe coding" (avec affichage live)

```bash
python demo_vibe_coding.py aegisai generate_login "Login"
python demo_vibe_coding.py aegisai generate_dashboard "Dashboard"
python demo_vibe_coding.py aegisai generate_navbar "Navbar"
```

Le fichier généré apparaît automatiquement dans `generated_projects/aegisai/src/...` — visible en direct dans l'explorateur de fichiers VS Code pendant l'exécution.

---

## Structure du projet démonstrateur (AegisAI)
- ✅ Prompt `generate_backend` — génère une vraie API FastAPI avec logique métier exécutable
- ✅ Backend testé en direct via Swagger (`/docs`) : 3 scénarios de budget validés (OK, alerte 80%, blocage 100%)

---

## Lancer le backend généré

```bash
pip install fastapi uvicorn
uvicorn generated_projects.aegisai.src.backend.budgetcheck:app --reload
```

Ouvre `http://localhost:8000/docs` pour tester l'API en direct (Swagger). Le backend applique réellement les règles de `business_rules.md` (alerte à 80%, blocage à 100%), avec les bons codes HTTP (200, 403, 404).
generated_projects/aegisai/
├── resources/
│   ├── business_rules.md
│   ├── project_context.md
│   └── coding_guidelines.md
└── src/
    ├── pages/
    │   ├── login.html
    │   ├── dashboard.html
    │   └── navbar.html
    └── backend/
        └── budgetcheck.py