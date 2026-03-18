import asyncio
from typing import Optional

from app.models.responses import ScoringJobResult


class JobStore:
    def __init__(self):
        self._store: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create(self, job_id: str, tenant_id: str) -> None:
        async with self._lock:
            self._store[job_id] = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "status": "processing",
            }

    async def get(self, job_id: str) -> Optional[ScoringJobResult]:
        async with self._lock:
            data = self._store.get(job_id)
        if data is None:
            return None
        return ScoringJobResult(**data)

    async def update(self, job_id: str, updates: dict) -> None:
        async with self._lock:
            if job_id in self._store:
                self._store[job_id].update(updates)


job_store = JobStore()
