from fastapi import APIRouter

from app.models.schemas import TextRequest, ExplainResponse, TermItem
from app.services.term_extractor import extract_terms
from app.services.stt_corrector import correct_stt_text

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
def explain_terms(request: TextRequest):
    # STT 교정 후 용어 추출 → 교정된 용어명으로 표시
    corrected_text = correct_stt_text(request.text, use_llm=True)
    terms_result = extract_terms(corrected_text)
    term_items = [TermItem(**term) for term in terms_result]
    return ExplainResponse(terms=term_items)
