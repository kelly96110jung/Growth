from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List


_TERMS_FILE = Path(__file__).resolve().parent.parent / "data" / "medical_terms.json"

def _load_fallback_terms() -> dict:
    try:
        with open(_TERMS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[terms] failed to load medical_terms.json: {e}")
        return {}


def _build_prompt(text: str) -> str:
    return f"""
너는 의료 용어 추출 시스템이다.

아래 텍스트에서 환자가 이해하기 어려울 수 있는 의료 용어, 검사명, 약물명, 진단명을 추출하라.

규칙:
1. 실제로 텍스트에 등장한 단어만 추출할 것
2. 각 용어에 대해 아래 두 가지를 함께 설명할 것:
   - 용어 자체의 의미 (2-3문장, 환자가 이해할 수 있도록 쉽게, 필요하면 예시나 비유 포함)
   - 이 텍스트에서 의사가 이 용어를 언급한 맥락과 이유 (1문장, 텍스트에 근거해서)
3. 너무 일반적인 단어(예: 치료, 병원, 의사)는 제외할 것
4. 최대 6개까지만 추출할 것
5. 출력은 JSON만 할 것

출력 형식:
{{
  "terms": [
    {{"term": "...", "description": "..."}}
  ]
}}

텍스트:
\"\"\"{text}\"\"\"
""".strip()


def _parse_response(raw: str) -> list[dict]:
    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    result = []
    for item in data.get("terms", []):
        term = str(item.get("term", "")).strip()
        description = str(item.get("description", "")).strip()
        if term and description:
            result.append({"term": term, "description": description})
    return result[:6]


def _fallback(text: str) -> list[dict]:
    fallback_terms = _load_fallback_terms()
    found = []
    for term, description in fallback_terms.items():
        if term in text:
            found.append({"term": term, "description": description})
    return found


def extract_terms(text: str) -> list[dict]:
    if not text or not text.strip():
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            prompt = _build_prompt(text)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            raw = (response.text or "").strip()
            result = _parse_response(raw)
            if result:
                return result
        except Exception as e:
            print(f"[terms] llm failed, fallback: {e}")

    return _fallback(text)
