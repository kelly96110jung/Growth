"""
STT 맥락 보정 서비스
- 1단계: 규칙 기반 교정 (척추 레벨, 알파벳/숫자 혼동 등)
- 2단계: LLM 기반 의료 용어 맥락 보정 (Gemini)
"""
from __future__ import annotations

import json
import os
import re

# ── 규칙 기반 교정 ──────────────────────────────────────────

# 척추 레벨 교정
# STT가 O(알파벳)를 0이나 5로 혼동하는 케이스 처리
_SPINAL_RULES = [
    # L4 LO → L4 L5 (연속된 요추 레벨에서 LO는 L5)
    (re.compile(r'\bL([1-4])\s+L[Oo0]\b'), r'L\1 L5'),
    (re.compile(r'\bL([1-4])-L[Oo0]\b'),   r'L\1-L5'),
    # 단독 LO → L5 (요추는 L1~L5, L0 없음)
    (re.compile(r'\bL[Oo0]\b'), 'L5'),
    # L1 L1 → L1-L2 (연속 레벨 붙여 쓰기 교정은 하지 않음, 오탐 방지)

    # 경추 C레벨 (C1~C7): CO → C0 아니라 C6 or C7 에 가까움, LLM에 맡김
    # 흉추 T레벨 (T1~T12)
    (re.compile(r'\bT([1-9])\s+T[Oo0]\b'), r'T\1 T10'),
    (re.compile(r'\bT([1-9])-T[Oo0]\b'),   r'T\1-T10'),

    # 디스크 레벨 표기 정규화: l4l5 → L4-L5
    (re.compile(r'\bl([1-5])l([1-5])\b', re.IGNORECASE), r'L\1-L\2'),
    (re.compile(r'\bc([1-7])c([1-7])\b', re.IGNORECASE), r'C\1-C\2'),
]

# 숫자/알파벳 혼동 (의료 문맥)
_CHAR_RULES = [
    # 검사 수치에서 소수점 앞뒤 O → 0
    (re.compile(r'(\d)[Oo](\d)'), r'\g<1>0\2'),   # 1O5 → 105
    (re.compile(r'(\d)[Oo]\b'),   r'\g<1>0'),      # 12O → 120
]


def rule_based_correct(text: str) -> str:
    """규칙 기반 1차 교정"""
    for pattern, repl in _SPINAL_RULES:
        text = pattern.sub(repl, text)
    for pattern, repl in _CHAR_RULES:
        text = pattern.sub(repl, text)
    return text


# ── LLM 기반 교정 ───────────────────────────────────────────

def _build_correction_prompt(text: str) -> str:
    return f"""
너는 의료 STT(음성인식) 교정 시스템이다.

아래 텍스트는 병원 진료 대화를 STT로 전사한 결과다.
STT 오류로 의료 용어가 잘못 인식된 부분을 교정하라.

교정 규칙:
1. 척추 레벨 표기 교정 (예: LO→L5, L4LO→L4-L5, C0→C6)
2. 알파벳과 숫자 혼동 교정 (예: 검사 수치 O→0)
3. 약어 오인식 교정 (예: 씨알피→CRP, 엠알아이→MRI)
4. 의미가 통하지 않는 단어만 교정할 것
5. 원문 내용을 임의로 추가하거나 삭제하지 말 것
6. 교정이 불필요하면 원문 그대로 반환할 것
7. 출력은 교정된 텍스트만 반환 (JSON 불필요, 설명 없이)

원문:
\"\"\"{text}\"\"\"
""".strip()


def llm_correct(text: str) -> str:
    """Gemini 기반 2차 교정"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return text

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=_build_correction_prompt(text),
            config=types.GenerateContentConfig(temperature=0.1),
        )
        corrected = (response.text or "").strip()
        # 빈 응답이면 원문 반환
        return corrected if corrected else text
    except Exception as e:
        print(f"[stt_corrector] llm correction failed: {e}")
        return text


def correct_stt_text(text: str, use_llm: bool = True) -> str:
    """
    STT 텍스트 전체 교정 파이프라인
    1. 규칙 기반 교정
    2. LLM 기반 교정 (use_llm=True일 때)
    """
    if not text or not text.strip():
        return text

    text = rule_based_correct(text)

    if use_llm:
        text = llm_correct(text)

    return text
