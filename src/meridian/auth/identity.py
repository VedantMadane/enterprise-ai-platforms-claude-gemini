import os
from typing import Optional
from fastapi import Request, HTTPException, status
from meridian.ingestion.directory_loader import Directory
from meridian.models.directory import User

def resolve_actor_from_request(
    request: Request,
    directory: Directory
) -> User:
    """
    Extracts simulated user identity from request headers, query parameters, or environment variables.
    Supported headers:
      - X-Actor-Email: user's email address
      - X-Actor-User-Id: user's directory ID
    Supported query params:
      - as_user: email or user_id
      - email: email
    """
    actor_id_or_email = (
        request.headers.get("X-Actor-Email")
        or request.headers.get("X-Actor-User-Id")
        or request.query_params.get("as_user")
        or request.query_params.get("email")
        or os.environ.get("MERIDIAN_ACTOR_EMAIL")
        or os.environ.get("MERIDIAN_ACTOR_ID")
    )

    if not actor_id_or_email:
        # Default to platform admin or team lead if none provided
        default_email = os.environ.get("MERIDIAN_DEFAULT_USER", "priya.nair@meridianls.example")
        actor_id_or_email = default_email

    user = directory.get_user(actor_id_or_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Simulated identity '{actor_id_or_email}' not found in Meridian directory."
        )
    return user
