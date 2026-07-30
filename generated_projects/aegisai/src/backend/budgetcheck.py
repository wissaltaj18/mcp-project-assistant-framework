from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict

# Initialisation du routeur FastAPI
router = APIRouter(prefix="/api/v1/budget", tags=["Budget"])

# Base de données en mémoire simulant l'état des budgets des projets
# Les montants sont exprimés dans une unité monétaire commune (ex: USD)
PROJECTS_DB: Dict[str, Dict[str, float]] = {
    "project-alpha": {
        "current_spend": 75.0,
        "budget_limit": 100.0
    },  # 75% consommé
    "project-beta": {
        "current_spend": 395.0,
        "budget_limit": 500.0
    },  # 79% consommé (proche alerte)
    "project-gamma": {
        "current_spend": 950.0,
        "budget_limit": 1000.0
    }, # 95% consommé (alerte déjà active)
    "project-delta": {
        "current_spend": 0.0,
        "budget_limit": 150.0
    }   # 0% consommé
}

# Modèles de données Pydantic
class BudgetCheckRequest(BaseModel):
    project_id: str = Field(..., description="Identifiant unique du projet")
    estimated_cost: float = Field(..., gt=0, description="Coût estimé de l'appel d'API IA")

class BudgetCheckResponse(BaseModel):
    status: str = Field(..., description="Statut de l'autorisation : 'approved'")
    project_id: str
    current_spend: float = Field(..., description="Dépenses cumulées après prise en compte de l'appel")
    budget_limit: float = Field(..., description="Limite budgétaire absolue du projet")
    alert_triggered: bool = Field(..., description="Vrai si le budget consommé dépasse ou atteint le seuil d'alerte de 80%")
    message: str

@router.post("/check", response_model=BudgetCheckResponse, status_code=status.HTTP_200_OK)
async def check_budget(request: BudgetCheckRequest):
    project_id = request.project_id
    estimated_cost = request.estimated_cost

    # Vérification de l'existence du projet
    if project_id not in PROJECTS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Le projet '{project_id}' n'existe pas dans le système de facturation."
        )

    project = PROJECTS_DB[project_id]
    current_spend = project["current_spend"]
    budget_limit = project["budget_limit"]
    new_spend = current_spend + estimated_cost

    # RÈGLE MÉTIER : Blocage strict à 100% du budget
    if new_spend > budget_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "BUDGET_EXCEEDED",
                "message": f"Appel refusé : Le coût estimé de {estimated_cost:.4f} dépasserait la limite budgétaire de {budget_limit:.2f} (Dépenses actuelles : {current_spend:.2f}).",
                "project_id": project_id,
                "current_spend": current_spend,
                "budget_limit": budget_limit,
                "estimated_cost": estimated_cost
            }
        )

    # RÈGLE MÉTIER : Alerte à partir de 80% du budget
    alert_threshold = budget_limit * 0.80
    alert_triggered = new_spend >= alert_threshold

    # Enregistrement et mise à jour de l'état (persistance en mémoire)
    PROJECTS_DB[project_id]["current_spend"] = new_spend

    # Construction du message d'accompagnement
    message = "Appel API autorisé."
    if alert_triggered:
        message += f" Attention : Le seuil d'alerte de 80% a été franchi ({new_spend:.2f} / {budget_limit:.2f})."

    return BudgetCheckResponse(
        status="approved",
        project_id=project_id,
        current_spend=new_spend,
        budget_limit=budget_limit,
        alert_triggered=alert_triggered,
        message=message
    )

@router.get("/status", response_model=Dict[str, Dict[str, float]], status_code=status.HTTP_200_OK)
async def get_budget_status():
    """
    Renvoie l'état actuel de TOUS les projets de manière brute,
    sans vérification ni modification d'état.
    """
    return PROJECTS_DB