"""Policy inspection endpoint.

The active security policy is readable so a reviewer can confirm what AEGIS-X
is actually enforcing, rather than taking the decisions on trust. Read-only:
editing policy is a reviewed change to the YAML file, not an API call.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.policy import Policy, PolicyError, get_policy

router = APIRouter(tags=["policy"])


@router.get("/policy", response_model=Policy, summary="The active security policy")
def read_policy() -> Policy:
    try:
        return get_policy()
    except PolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "policy_invalid", "message": str(exc)},
        ) from exc
