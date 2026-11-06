from fastapi import APIRouter

from tailor.api import health, llm

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(llm.router)
