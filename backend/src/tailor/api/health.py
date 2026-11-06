from fastapi import APIRouter
from pydantic import BaseModel

from tailor import __version__
from tailor.db import SessionDep

router = APIRouter(tags=["système"])


class Health(BaseModel):
    status: str
    version: str
    database: str


@router.get("/health")
def health(session: SessionDep) -> Health:
    session.connection().exec_driver_sql("SELECT 1")
    return Health(status="ok", version=__version__, database="ok")
