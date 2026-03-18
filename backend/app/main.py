import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import scoring
from app.config import get_settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Summary Feedback Scoring API", version="1.0.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scoring.router, prefix="/v1")
