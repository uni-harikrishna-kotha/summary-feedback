from typing import Optional

from pydantic import BaseModel


class ScoringRunRequest(BaseModel):
    tenant_id: str
    jwt_token: str
    environment: str = "prod"
    summary_template: str
    experience_id: Optional[str] = None
