from fastapi import APIRouter

from app.models.schemas import TextRequest, SummaryResponse, StructuredInfo
from app.services.summarizer import summarize_text
from app.services.stt_corrector import correct_stt_text

router = APIRouter()


@router.post("/summary", response_model=SummaryResponse)
def summarize(request: TextRequest):
    # LLM 기반 STT 교정 → 교정된 텍스트로 요약
    corrected_text = correct_stt_text(request.text, use_llm=True)
    result = summarize_text(corrected_text)
    structured = StructuredInfo(
        symptoms=result.get("symptoms", []),
        measurements=result.get("measurements", []),
        medications=result.get("medications", []),
    )
    return SummaryResponse(summary=result.get("summary", []), structured=structured)
