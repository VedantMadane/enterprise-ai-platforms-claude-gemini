from typing import List, Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str # "member", "team_lead", "platform_admin"
    group_ids: List[str] = Field(default_factory=list)
    claude_seat: bool = True
    gcp_principal: Optional[str] = None

    @property
    def primary_group(self) -> Optional[str]:
        return self.group_ids[0] if self.group_ids else None

class Group(BaseModel):
    group_id: str
    name: str
    team_lead_user_id: str
    claude_rbac_group_id: str
    gcp_project_id: str
    gcp_project_number: Optional[str] = None
    cost_centre: Optional[str] = None
