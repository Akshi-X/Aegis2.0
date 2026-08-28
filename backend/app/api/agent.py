"""Autonomous agent endpoint.

This module has no access to the bank simulator. ``app.services.bank`` is not
imported, and the agent service can only produce PROPOSED proposals -- the
"agent cannot execute" guarantee is structural, not a runtime check that could
be bypassed.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AgentNotFoundError,
    InstructionParseError,
    NoSourceAccountError,
)
from app.database.session import get_db
from app.schemas.agent import ActionProposalRead, AgentTaskRequest, AgentTaskResponse, FinancialDNAProfile, AgentOverview, DashboardMetricsResponse
from app.services import agent as agent_service
from app.services.engines.financial_dna import FinancialDNAService
from app.services.engines.base import EvaluationContext
from app.models import Agent, ActionProposal, Transaction
from app.models.enums import AgentStatus, ProposalStatus

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
    summary="Get aggregated dashboard metrics",
)
def get_dashboard_metrics(db: Session = Depends(get_db)) -> DashboardMetricsResponse:
    # 1. Active agents
    active_agents = db.scalar(
        select(func.count()).select_from(Agent).where(Agent.status == AgentStatus.ACTIVE)
    ) or 0

    # 2. Average trust score
    avg_trust = db.scalar(
        select(func.avg(Agent.trust_score)).where(Agent.status == AgentStatus.ACTIVE)
    )
    avg_trust = float(avg_trust) if avg_trust is not None else 0.0

    # 3. Actions today (proposals created in last 24h)
    # Using simple date filtering for demonstration
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    
    actions_today = db.scalar(
        select(func.count()).select_from(ActionProposal).where(ActionProposal.created_at >= one_day_ago)
    ) or 0

    # 4. Executed actions today (transactions created in last 24h)
    executed_actions = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.timestamp >= one_day_ago)
    ) or 0

    # 5. Blocked actions today (proposals that were blocked in last 24h)
    blocked_actions = db.scalar(
        select(func.count()).select_from(ActionProposal).where(
            ActionProposal.created_at >= one_day_ago,
            ActionProposal.status == ProposalStatus.BLOCKED
        )
    ) or 0

    return DashboardMetricsResponse(
        active_agents=active_agents,
        actions_today=actions_today,
        executed_actions=executed_actions,
        blocked_actions=blocked_actions,
        average_trust=round(avg_trust, 1),
    )


@router.get(
    "",
    response_model=list[AgentOverview],
    summary="List all agents",
)
def list_agents(db: Session = Depends(get_db)) -> list[AgentOverview]:
    agents = db.scalars(select(Agent)).all()
    return [AgentOverview.model_validate(a) for a in agents]


@router.get(
    "/{agent_id}",
    response_model=AgentOverview,
    summary="Get agent details",
    responses={
        404: {"description": "Agent does not exist"},
    },
)
def get_agent(agent_id: int, db: Session = Depends(get_db)) -> AgentOverview:
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "agent_not_found", "message": f"Agent {agent_id} not found"},
        )
    return AgentOverview.model_validate(agent)


@router.post(
    "/task",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Give the agent a natural-language task",
    responses={
        404: {"description": "Agent does not exist"},
        422: {"description": "Instruction could not be understood"},
        409: {"description": "Agent has no source account"},
    },
)
def submit_task(
    payload: AgentTaskRequest, db: Session = Depends(get_db)
) -> AgentTaskResponse:
    try:
        proposal = agent_service.create_proposal(
            db,
            agent_ref=payload.agent_id,
            task=payload.task,
            context=payload.context,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except NoSourceAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except InstructionParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": exc.code,
                "message": exc.message,
                "provider": exc.provider,
            },
        ) from exc

    parser_detail = (proposal.provenance or {}).get("parser", {})

    return AgentTaskResponse(
        proposal=ActionProposalRead.model_validate(proposal),
        parser=parser_detail.get("provider", "unknown"),
        fallback_used=bool(parser_detail.get("fallback_used", False)),
    )

@router.get(
    "/{agent_id}/financial-dna",
    response_model=FinancialDNAProfile,
    summary="Get the agent's normal behavioural profile",
    responses={
        404: {"description": "Agent does not exist"},
    },
)
def get_financial_dna(
    agent_id: int, db: Session = Depends(get_db)
) -> FinancialDNAProfile:
    # Get agent
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "agent_not_found", "message": f"Agent {agent_id} not found"},
        )
        
    context = EvaluationContext(
        db=db,
        proposal=None,
        agent=agent,
        source_account=agent.source_account,
        now=datetime.now(timezone.utc)
    )
    
    svc = FinancialDNAService()
    profile = svc.get_profile(context)
    
    return FinancialDNAProfile(
        agent_id=agent.id,
        **profile
    )
