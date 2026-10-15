from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

class PeriodWindow(BaseModel):
    start: str
    end_exclusive: str

class PlatformTotals(BaseModel):
    platform: Literal["claude", "gemini"]
    requests: Optional[int] = None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

class OverallTotals(BaseModel):
    total_tokens: int
    cost_usd: float

class UsageSummaryResponse(BaseModel):
    group: str
    period: PeriodWindow
    platforms: List[PlatformTotals]
    totals: OverallTotals

class TopUser(BaseModel):
    user_id: str
    name: str
    email: Optional[str] = None
    group: str
    total_tokens: int
    cost_usd: float

class UnifiedUsageRecord(BaseModel):
    id: str
    platform: Literal["claude", "gemini"]
    user_id: str
    user_name: str
    user_email: str
    group_id: str
    date: str # YYYY-MM-DD
    iso_week: str # YYYY-Www
    product_or_agent: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    requests: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
