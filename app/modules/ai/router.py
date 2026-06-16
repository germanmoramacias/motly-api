from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.ai.schemas import TutorChatRequest, TutorChatResponse
from app.modules.ai.service import OpenAIService
from app.modules.auth.router import get_current_claims
from app.shared.security import SupabaseJWTClaims

router = APIRouter()


def get_openai_service() -> OpenAIService:
    return OpenAIService()


@router.post("/chat", response_model=TutorChatResponse)
async def chat(
    payload: TutorChatRequest,
    _: SupabaseJWTClaims = Depends(get_current_claims),
    service: OpenAIService = Depends(get_openai_service),
) -> TutorChatResponse:
    message = await service.chat_with_tutor(payload.messages)
    return TutorChatResponse(message=message)
