from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from tailor.api import health, llm, profile, settings
from tailor.llm.errors import CloudCallBlocked, LLMError
from tailor.profile.service import ProfileError

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(llm.router)
api_router.include_router(profile.router)
api_router.include_router(settings.router)


def install_error_handlers(app: FastAPI) -> None:
    """Traduit les erreurs métier en réponses HTTP lisibles par l'interface."""

    @app.exception_handler(ProfileError)
    async def _profile_error(_request: Request, error: ProfileError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=error.status)

    @app.exception_handler(CloudCallBlocked)
    async def _blocked(_request: Request, error: CloudCallBlocked) -> JSONResponse:
        # Garde-fou (consentement, mode local strict, plafond) : action requise de l'utilisateur.
        return JSONResponse({"detail": str(error), "code": "llm_blocked"}, status_code=409)

    @app.exception_handler(LLMError)
    async def _llm_error(_request: Request, error: LLMError) -> JSONResponse:
        return JSONResponse({"detail": str(error), "code": "llm_error"}, status_code=502)
