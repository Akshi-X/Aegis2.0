"""Action proposals: read access, and submission to the AEGIS-X pipeline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import ProposalNotFoundError
from app.database.session import get_db
from app.models.enums import ProposalStatus
from app.schemas.agent import ActionProposalRead
from app.schemas.evaluation import ActionEvaluationRead, EvaluationResponse
from app.services import agent as agent_service
from app.services import orchestrator as orchestrator_service
from app.services.orchestrator import AegisOrchestrator

router = APIRouter(tags=["actions"])


@router.get(
    "/actions",
    response_model=list[ActionProposalRead],
    summary="List action proposals (newest first)",
)
def list_actions(
    agent_id: int | None = Query(default=None),
    proposal_status: ProposalStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ActionProposalRead]:
    return agent_service.list_proposals(
        db,
        agent_id=agent_id,
        status=proposal_status.value if proposal_status else None,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/actions/{action_id}",
    response_model=ActionProposalRead,
    summary="Fetch one proposal by action_id (or numeric id)",
)
def get_action(action_id: str, db: Session = Depends(get_db)) -> ActionProposalRead:
    proposal = agent_service.get_proposal(db, action_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "action_not_found",
                "message": f"No action proposal matching {action_id!r}.",
            },
        )
    return proposal


@router.post(
    "/actions/{action_id}/evaluate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run the AEGIS-X security evaluation pipeline",
    responses={404: {"description": "Action proposal does not exist"}},
)
def evaluate_action(
    action_id: str, db: Session = Depends(get_db)
) -> EvaluationResponse:
    """Evaluate a proposal and record the decision.

    Re-evaluating is permitted and writes a new evaluation record rather than
    overwriting the previous one. Nothing is executed as a result.
    """
    try:
        proposal = orchestrator_service.get_proposal_for_evaluation(db, action_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    # A proposal whose agent no longer exists is not an error here: the
    # Authority engine reports AGENT_NOT_FOUND and governance blocks it.
    evaluation = AegisOrchestrator().evaluate(db, proposal)

    return EvaluationResponse(
        evaluation=ActionEvaluationRead.model_validate(evaluation),
        proposal=ActionProposalRead.model_validate(proposal),
    )


@router.get(
    "/actions/{action_id}/evaluations",
    response_model=list[ActionEvaluationRead],
    summary="Evaluation history for a proposal (newest first)",
)
def list_action_evaluations(
    action_id: str, db: Session = Depends(get_db)
) -> list[ActionEvaluationRead]:
    try:
        proposal = orchestrator_service.get_proposal_for_evaluation(db, action_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    return orchestrator_service.list_evaluations(db, proposal_id=proposal.id)
