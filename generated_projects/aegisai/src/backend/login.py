from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any

# Initialisation du routeur FastAPI pour l'authentification
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

# =====================================================================
# ATTENTION : Base de données de démonstration en mémoire.
# Dans une application de production réelle :
# 1. Ne stockez JAMAIS les mots de passe en clair. Utilisez un algorithme
#    de hachage sécurisé comme bcrypt ou Argon2.
# 2. Utilisez une vraie base de données (ex: PostgreSQL comme mentionné
#    dans le contexte AegisAI) au lieu d'un dictionnaire global.
# 3. Le compteur de tentatives devrait être géré dans un cache rapide
#    et temporaire (comme Redis) pour expirer après un certain temps.
# =====================================================================

# Structure de la base de données utilisateur fictive
# Les rôles correspondent strictement au contexte de gouvernance AegisAI :
# - admin : Gestion des budgets, validation des dépassements, conformité
# - team_lead : Suivi de la consommation d'équipe
# - developer : Consommation des APIs IA
USERS_DB = {
    "wissal": {
        "username": "clara.admin@aegis.ai",
        "password": "wissal123",  # À hacher en production !
        "role": "admin",
        "failed_attempts": 0
    },
    "thomas.lead@aegis.ai": {
        "username": "thomas.lead@aegis.ai",
        "password": "leadsecretpass",  # À hacher en production !
        "role": "team_lead",
        "failed_attempts": 0
    },
    "lucas.dev@aegis.ai": {
        "username": "lucas.dev@aegis.ai",
        "password": "devsecretpass",  # À hacher en production !
        "role": "developer",
        "failed_attempts": 0
    }
}

# Modèles de données Pydantic pour l'API
class LoginRequest(BaseModel):
    username: str = Field(..., example="clara.admin@aegis.ai")
    password: str = Field(..., example="adminsecretpass")

class LoginResponse(BaseModel):
    username: str
    role: str
    message: str


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    username = credentials.username
    password = credentials.password

    # 1. Vérification de l'existence de l'utilisateur
    if username not in USERS_DB:
        # Pour éviter l'énumération d'utilisateurs, on renvoie une erreur générique 401.
        # Néanmoins, pour ne pas saturer la mémoire avec des utilisateurs inexistants,
        # la limitation stricte de tentatives (429) ne s'applique ici qu'aux comptes existants.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects."
        )

    user = USERS_DB[username]

    # 2. Vérification du verrouillage du compte (Sécurité anti-brute force)
    if user["failed_attempts"] >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Compte verrouillé temporairement en raison de trop nombreuses tentatives de connexion (3 échecs consécutifs)."
        )

    # 3. Validation du mot de passe (En clair pour la démo)
    if user["password"] != password:
        # Incrémentation du compteur de tentatives infructueuses
        user["failed_attempts"] += 1
        
        # Message dynamique pour notifier l'utilisateur du nombre d'essais restants
        attempts_left = 3 - user["failed_attempts"]
        if attempts_left == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Compte verrouillé temporairement en raison de trop nombreuses tentatives de connexion."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Identifiants incorrects. Tentatives restantes avant verrouillage : {attempts_left}."
            )

    # 4. Authentification réussie
    # Réinitialisation des tentatives échouées après un succès
    user["failed_attempts"] = 0

    return LoginResponse(
        username=user["username"],
        role=user["role"],
        message="Authentification réussie sur la plateforme AegisAI."
    )