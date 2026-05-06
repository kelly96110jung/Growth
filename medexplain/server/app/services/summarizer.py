import json
import os
import re
from typing import List, Optional

from google import genai
from google.genai import types


def _normalize_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if len(text) > 6000:
        text = text[:6000]
    return text


def summarize_text_rule_based(text: str) -> List[str]:
    text = _normalize_text(text)
    if not text:
        return []

    # 소수점(0.5, 1.2 등)은 분리하지 않고, 문장 끝 마침표/느낌표/물음표 기준으로만 분리
    sentences = re.split(r'(?<!\d)\.(?!\d)\s*|[!?]\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    result = []
    for sentence in sentences[:3]:
        result.append(sentence if sentence.endswith(".") else sentence + ".")
    return result


def _build_prompt(text: str) -> str:
    return f"""
너는 환자가 진료 내용을 이해할 수 있도록 돕는 요약 도우미다.

아래는 병원 진료 대화를 STT로 전사한 텍스트다.
의사의 설명을 처음 듣는 환자가 "오늘 진료에서 뭘 들었지?"를 한눈에 파악할 수 있도록 요약하라.

요약 방식:
- 원문을 그대로 줄이는 것이 아니라, 핵심 정보를 환자 언어로 재구성할 것
- 의학 용어는 쉬운 말로 풀되, 실제 수치는 반드시 괄호로 병기할 것 (예: "염증 수치가 기준보다 높게 나왔다 (CRP 3.2)", "혈당이 당뇨 직전 수준이다 (공복혈당 128, HbA1c 6.8%)")
- 환자에게 중요한 순서로 작성할 것 (진단/결과 → 치료 방향 → 주의사항)
- 각 bullet은 1~2문장, 누가 봐도 이해되는 쉬운 한국어로 작성

지킬 규칙:
1. 원문에 없는 내용은 추가하지 말 것
2. 진단명은 의사가 언급한 것만 쓸 것 (임의 추론 금지)
3. 최대 3개 bullet
4. 수치(0.5, L4-L5 등)는 정확하게 유지할 것
5. 출력은 JSON만 할 것

출력 형식:
{{
  "summary": ["문장1", "문장2", "문장3"],
  "symptoms": ["증상1", "증상2"],
  "measurements": ["검사명 수치 단위"],
  "medications": ["약물명 용량"]
}}

입력 텍스트:
\"\"\"{text}\"\"\"
""".strip()


def _parse_llm_summary(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    if not raw_text:
        return {}

    raw_text = re.sub(r"^```json\s*", "", raw_text)
    raw_text = re.sub(r"^```\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    data = json.loads(raw_text)

    summary = [s.strip() for s in data.get("summary", []) if isinstance(s, str) and s.strip()][:3]
    symptoms = [s.strip() for s in data.get("symptoms", []) if isinstance(s, str) and s.strip()]
    measurements = [s.strip() for s in data.get("measurements", []) if isinstance(s, str) and s.strip()]
    medications = [s.strip() for s in data.get("medications", []) if isinstance(s, str) and s.strip()]

    return {
        "summary": summary,
        "symptoms": symptoms,
        "measurements": measurements,
        "medications": medications,
    }


def summarize_text_llm(text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(text)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )

    raw_text = (response.text or "").strip()
    result = _parse_llm_summary(raw_text)

    if not result.get("summary"):
        raise RuntimeError("LLM returned empty or invalid summary")

    return result


def summarize_text(text: str) -> dict:
    """
    반환값: {"summary": [...], "symptoms": [...], "measurements": [...], "medications": [...]}
    """
    text = _normalize_text(text)
    if not text:
        return {"summary": [], "symptoms": [], "measurements": [], "medications": []}

    try:
        result = summarize_text_llm(text)
        if result.get("summary"):
            return result
    except Exception as e:
        print(f"[summary] llm failed, fallback to rule-based: {e}")

    return {
        "summary": summarize_text_rule_based(text),
        "symptoms": [],
        "measurements": [],
        "medications": [],
    }
