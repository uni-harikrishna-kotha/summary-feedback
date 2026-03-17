from pydantic import BaseModel


class ScoringRunRequest(BaseModel):
    tenant_id: str
    jwt_token: str
