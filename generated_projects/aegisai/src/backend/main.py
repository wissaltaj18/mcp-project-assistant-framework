"""
Point d'entrée backend UNIQUE pour AegisAI. Assemble tous les routers
générés (budget, auth...) en une seule application FastAPI, sur un seul
port -- plutôt que de lancer un serveur séparé par fonctionnalité.

Lancer avec :
    uvicorn generated_projects.aegisai.src.backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from generated_projects.aegisai.src.backend.budgetcheck import router as budget_router
from generated_projects.aegisai.src.backend.login import router as auth_router

app = FastAPI(
    title="AegisAI - Plateforme de Gouvernance IA",
    description="API unifiée : gouvernance budgétaire et authentification.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(budget_router)
app.include_router(auth_router)