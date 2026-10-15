from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from meridian.auth.identity import resolve_actor_from_request
from meridian.auth.rbac import RBACPolicy
from meridian.models.capabilities import Capability, CapabilityControl
from meridian.models.directory import User, Group
from meridian.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/api", tags=["admin"])

def get_store(request: Request) -> SQLiteStore:
    return request.app.state.store

def get_rbac(request: Request) -> RBACPolicy:
    return request.app.state.rbac

def get_current_user(request: Request) -> User:
    return resolve_actor_from_request(request, request.app.state.directory)

class CapabilityUpdateRequest(BaseModel):
    group: str
    capability: Capability
    enabled: bool

@router.get("/me")
def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    rbac: RBACPolicy = Depends(get_rbac)
):
    write_roles = rbac.config.get("scopes", {}).get("capabilities:write", {}).get("roles", [])
    read_roles = rbac.config.get("scopes", {}).get("usage:read", {}).get("roles", [])
    visibility = rbac.config.get("scopes", {}).get("usage:read", {}).get("group_visibility", "own_group")
    
    can_write = current_user.role in write_roles
    can_read = current_user.role in read_roles

    return {
        "user_id": current_user.user_id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "group_ids": current_user.group_ids,
        "primary_group": current_user.primary_group,
        "environment": rbac.env_name,
        "permissions": {
            "can_read_usage": can_read,
            "can_write_capabilities": can_write,
            "group_visibility": visibility,
            "is_admin": current_user.role == "platform_admin"
        }
    }

@router.get("/directory/users", response_model=List[User])
def list_directory_users(request: Request):
    return request.app.state.directory.users

@router.get("/directory/groups", response_model=List[Group])
def list_directory_groups(request: Request):
    return request.app.state.directory.groups

@router.get("/capabilities", response_model=List[CapabilityControl])
def get_capabilities(
    group: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    store: SQLiteStore = Depends(get_store),
    rbac: RBACPolicy = Depends(get_rbac)
):
    # In prod/staging, non-admins can only see their own group's capabilities if restricted
    if current_user.role != "platform_admin" and rbac.config.get("scopes", {}).get("usage:read", {}).get("group_visibility") == "own_group":
        if group and group != current_user.primary_group:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "permission_denied",
                    "reason": f"Caller '{current_user.name}' cannot view capabilities for group '{group}'."
                }
            )
        group = current_user.primary_group

    return store.get_capabilities(group_id=group)

@router.post("/capabilities", response_model=CapabilityControl)
def set_capability(
    payload: CapabilityUpdateRequest,
    current_user: User = Depends(get_current_user),
    store: SQLiteStore = Depends(get_store),
    rbac: RBACPolicy = Depends(get_rbac)
):
    allowed, denial = rbac.check_capabilities_write(current_user, payload.group)
    if not allowed or denial:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial.model_dump()
        )

    updated = store.set_capability(
        group_id=payload.group,
        capability=payload.capability.value,
        enabled=payload.enabled,
        actor=current_user.email
    )
    return updated
