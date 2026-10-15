from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from meridian.auth.identity import resolve_actor_from_request
from meridian.auth.rbac import RBACPolicy
from meridian.models.directory import User
from meridian.models.unified import UsageSummaryResponse, TopUser
from meridian.store.periods import parse_period
from meridian.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/api/usage", tags=["usage"])

def get_store(request: Request) -> SQLiteStore:
    return request.app.state.store

def get_rbac(request: Request) -> RBACPolicy:
    return request.app.state.rbac

def get_current_user(request: Request) -> User:
    return resolve_actor_from_request(request, request.app.state.directory)

@router.get("/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    group: Optional[str] = Query(None, description="Group ID or omitted for caller's group"),
    period: str = Query("last_30_days", description="last_7_days | last_30_days | YYYY-Www | YYYY-MM"),
    current_user: User = Depends(get_current_user),
    store: SQLiteStore = Depends(get_store),
    rbac: RBACPolicy = Depends(get_rbac)
):
    try:
        window = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    allowed, resolved_group, denial = rbac.check_usage_read(current_user, group, store=store)
    if not allowed or denial:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial.model_dump()
        )

    summary = store.get_usage_summary(resolved_group, window)
    return summary

@router.get("/top-users", response_model=List[TopUser])
def get_top_users(
    group: Optional[str] = Query(None, description="Group ID or omitted for caller's group"),
    period: str = Query("last_30_days", description="last_7_days | last_30_days | YYYY-Www | YYYY-MM"),
    limit: int = Query(10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
    store: SQLiteStore = Depends(get_store),
    rbac: RBACPolicy = Depends(get_rbac)
):
    try:
        window = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    allowed, resolved_group, denial = rbac.check_usage_read(current_user, group, store=store)
    if not allowed or denial:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial.model_dump()
        )

    return store.get_top_users(resolved_group, window, limit=limit)

@router.get("/by-group-and-week")
def get_by_group_and_week(
    current_user: User = Depends(get_current_user),
    store: SQLiteStore = Depends(get_store),
    rbac: RBACPolicy = Depends(get_rbac)
):
    allowed, _, denial = rbac.check_usage_read(current_user, None, store=store)
    if not allowed or denial:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial.model_dump()
        )

    all_data = store.get_usage_by_group_and_week()
    if current_user.role != "platform_admin" and rbac.config.get("scopes", {}).get("usage:read", {}).get("group_visibility") == "own_group":
        caller_group = current_user.primary_group
        return [d for d in all_data if d["group_id"] == caller_group]
    return all_data
