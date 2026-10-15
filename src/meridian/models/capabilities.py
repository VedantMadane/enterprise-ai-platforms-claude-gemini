from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Capability(str, Enum):
    USAGE_CONNECTOR = "usage-connector"
    WEB_SEARCH = "web-search"
    CODE_EXECUTION = "code-execution"

class CapabilityControl(BaseModel):
    group: str
    capability: Capability
    enabled: bool
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

class Denial(BaseModel):
    error: str = "permission_denied"
    reason: str
    required_scope: Optional[str] = None
