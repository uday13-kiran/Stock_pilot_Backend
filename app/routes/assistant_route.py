from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.assistant_service import ask_llm


router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


class AssistantAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    warehouse_id: int | None = Field(default=None, gt=0)


@router.post("/ask")
def ask_assistant(payload: AssistantAskRequest, db: Session = Depends(get_db)):
    return ask_llm(payload.question, payload.warehouse_id, db)
