from __future__ import annotations

import asyncio
import base64
import io
import os
import queue
import re
import threading
import wave
from dataclasses import dataclass
from typing import Callable, Optional

from google.cloud import speech_v1 as speech

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\82107\Downloads\medexplain-stt-13e7cf056287.json"

# 한국어 숫자 → 아라비아 숫자 매핑 (단독 수치 표현)
_KO_NUMBER_MAP = {
    "영": "0", "일": "1", "이": "2", "삼": "3", "사": "4",
    "오": "5", "육": "6", "칠": "7", "팔": "8", "구": "9",
    "십": "10", "백": "100", "천": "1000",
}

# 소수점 구어체 표현: "영점오" → "0.5", "일점이오" → "1.25"
_DECIMAL_PATTERN = re.compile(
    r"([영일이삼사오육칠팔구십]+)점([영일이삼사오육칠팔구십]+)"
)

# 자주 오인식되는 의료 약어 → 표준 표기
_ABBR_CORRECTIONS = {
    "씨알피": "CRP",
    "씨비씨": "CBC",
    "엠알아이": "MRI",
    "씨티": "CT",
    "피이티": "PET",
    "에이치비에이원씨": "HbA1c",
    "당화혈색소": "HbA1c",
    "이지에프알": "eGFR",
    "피에스에이": "PSA",
    "티에스에이치": "TSH",
    "아이엔알": "INR",
    "비엠아이": "BMI",
}

# 단위 구어체 → 표준 단위
_UNIT_CORRECTIONS = {
    "밀리그램": "mg",
    "마이크로그램": "μg",
    "밀리리터": "mL",
    "밀리몰": "mmol",
    "밀리미터": "mm",
    "센티미터": "cm",
    "퍼센트": "%",
    "프로": "%",
    "엠엠에이치지": "mmHg",
}

# 필터링할 구어체 간투사 (단어 단위로만 제거)
_FILLER_PATTERN = re.compile(
    r"\b(음+|아+|어+|그+|저+|뭐+|에+)\b\.?\s*", re.UNICODE
)


def _fix_decimal(match: re.Match) -> str:
    """"영점오" 형식의 소수 표현을 "0.5"로 변환"""
    integer_part = match.group(1)
    decimal_part = match.group(2)
    int_val = "".join(_KO_NUMBER_MAP.get(c, c) for c in integer_part)
    dec_val = "".join(_KO_NUMBER_MAP.get(c, c) for c in decimal_part)
    return f"{int_val}.{dec_val}"


def postprocess_stt_text(text: str) -> str:
    """
    STT 결과 텍스트 후처리:
    1. 의료 약어 오인식 교정 (씨알피 → CRP)
    2. 단위 구어체 표준화 (밀리그램 → mg)
    3. 소수점 구어체 변환 (영점오 → 0.5)
    4. 간투사 제거 (음, 아, 어 등)
    5. 척추 레벨 등 규칙 기반 의료 용어 교정
    """
    if not text:
        return text

    # 약어 교정
    for ko, en in _ABBR_CORRECTIONS.items():
        text = re.sub(ko, en, text, flags=re.IGNORECASE)

    # 단위 교정
    for ko, unit in _UNIT_CORRECTIONS.items():
        text = re.sub(ko, unit, text)

    # 소수점 변환
    text = _DECIMAL_PATTERN.sub(_fix_decimal, text)

    # 간투사 제거
    text = _FILLER_PATTERN.sub("", text)

    # 다중 공백 정리
    text = re.sub(r" {2,}", " ", text).strip()

    # 규칙 기반 의료 용어 교정 (척추 레벨 등)
    from app.services.stt_corrector import rule_based_correct
    text = rule_based_correct(text)

    return text


@dataclass
class AudioFormat:
    encoding: str  # "LINEAR16"
    sample_rate_hz: int
    channels: int


def _looks_like_wav(raw: bytes) -> bool:
    return len(raw) >= 12 and raw[0:4] == b"RIFF" and raw[8:12] == b"WAVE"


def wav_bytes_to_pcm16(raw_wav: bytes) -> tuple[bytes, AudioFormat]:
    """
    WAV 컨테이너 bytes -> PCM16(raw) bytes + format
    """
    with wave.open(io.BytesIO(raw_wav), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm = wf.readframes(wf.getnframes())

    if sample_width != 2:
        raise ValueError(f"WAV must be 16-bit PCM. got sample_width={sample_width}")

    return pcm, AudioFormat(encoding="LINEAR16", sample_rate_hz=sample_rate, channels=channels)


def _medical_phrase_hints() -> list[str]:
    return [
        # 영어 검사명/진단명
        "CRP", "CBC", "CT", "MRI", "PET-CT", "PET CT",
        "biopsy", "endoscopy", "gastroscopy", "gastrectomy",
        "chemotherapy", "radiotherapy", "adenocarcinoma",
        "gastric adenocarcinoma", "carcinoma", "metastasis",
        "lymph node", "lymph nodes", "lymphatic invasion",
        "cancer", "stomach cancer",
        "HbA1c", "eGFR", "PSA", "TSH", "INR", "BMI",
        # 한국어 검사명/진단명
        "위선암", "위암", "조직 검사", "내시경", "항암화학요법",
        "방사선 치료", "림프절", "림프절 전이", "전이",
        "혈당", "공복 혈당", "당화혈색소", "혈압", "맥박",
        "크레아티닌", "헤모글로빈", "백혈구", "적혈구", "혈소판",
        "초음파", "조영제", "생검", "세침 흡인", "복강경",
        "고혈압", "당뇨", "고지혈증", "갑상선", "심부전",
        "부정맥", "협심증", "심근경색", "뇌졸중", "폐렴",
        # 수치/숫자 표현
        "밀리그램", "마이크로그램", "밀리리터",
        "퍼센트", "프로", "배",
        "수축기", "이완기",
        "정상 범위", "정상 수치", "기준치",
    ]


def _build_recognition_config(sample_rate: int, channels: int) -> speech.RecognitionConfig:
    """
    공통 RecognitionConfig 생성
    - 한국어 기반 유지
    - 영어 의료용어 phrase hints 추가
    """
    speech_context = speech.SpeechContext(
        phrases=_medical_phrase_hints(),
        boost=25.0,
    )

    return speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code="ko-KR",
        alternative_language_codes=["en-US"],
        enable_automatic_punctuation=True,
        audio_channel_count=channels,
        model="latest_long",
        use_enhanced=True,
        speech_contexts=[speech_context],
    )


class GoogleStreamingSttBridge:

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        on_result: Callable[[str, bool], None],
        on_error: Callable[[str], None],
    ):
        self.loop = loop
        self.on_result = on_result
        self.on_error = on_error

        self._fmt: Optional[AudioFormat] = None
        self._q: "queue.Queue[Optional[bytes]]" = queue.Queue()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def set_audio_format(self, *, encoding: str, sample_rate_hz: int, channels: int) -> None:
        if encoding != "LINEAR16":
            raise ValueError("Only LINEAR16 is supported in v0")
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        if channels not in (1, 2):
            raise ValueError("channels must be 1 or 2")
        self._fmt = AudioFormat(encoding=encoding, sample_rate_hz=sample_rate_hz, channels=channels)

    def start_streaming_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_streaming, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._q.put(None)

    def enqueue_audio_bytes(self, raw: bytes) -> tuple[int, bool]:
        was_wav = False
        if _looks_like_wav(raw):
            was_wav = True
            pcm, _fmt_from_wav = wav_bytes_to_pcm16(raw)
            raw = pcm

        self._q.put(raw)
        return (len(raw), was_wav)

    def recognize_once(self, raw: bytes) -> None:
        """
        record-then-send 모드용: 한 번에 받은 오디오를 단발 recognize로 처리.
        (Streaming Audio Timeout 회피)
        """
        try:
            if not self._fmt:
                raise RuntimeError("Audio format is not set. Call set_audio_format() first.")

            if _looks_like_wav(raw):
                pcm, fmt_from_wav = wav_bytes_to_pcm16(raw)
                pcm_bytes = pcm
                sample_rate = fmt_from_wav.sample_rate_hz
                channels = fmt_from_wav.channels
            else:
                pcm_bytes = raw
                sample_rate = self._fmt.sample_rate_hz
                channels = self._fmt.channels

            config = _build_recognition_config(sample_rate, channels)
            audio = speech.RecognitionAudio(content=pcm_bytes)

            client = speech.SpeechClient()
            resp = client.recognize(config=config, audio=audio)

            if not resp.results:
                self._emit_result("", True)
                return

            texts: list[str] = []
            for r in resp.results:
                if r.alternatives:
                    texts.append(r.alternatives[0].transcript)

            final_text = " ".join(t.strip() for t in texts if t and t.strip())
            self._emit_result(postprocess_stt_text(final_text), True)

        except Exception as e:
            self._emit_error(f"{type(e).__name__}: {e}")

    def _emit_result(self, text: str, is_final: bool) -> None:
        self.loop.call_soon_threadsafe(self.on_result, text, is_final)

    def _emit_error(self, msg: str) -> None:
        self.loop.call_soon_threadsafe(self.on_error, msg)

    def _request_generator(self):
        first = self._q.get()
        if first is None:
            return

        if not self._fmt:
            raise RuntimeError("Audio format is not set. Call set_audio_format() after session.start.")

        config = _build_recognition_config(
            sample_rate=self._fmt.sample_rate_hz,
            channels=self._fmt.channels,
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
            single_utterance=False,
        )

        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        yield speech.StreamingRecognizeRequest(audio_content=first)

        while not self._stop.is_set():
            chunk = self._q.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def _run_streaming(self) -> None:
        try:
            client = speech.SpeechClient()

            responses = client.streaming_recognize(requests=self._request_generator())

            for resp in responses:
                for result in resp.results:
                    if not result.alternatives:
                        continue
                    text = result.alternatives[0].transcript
                    processed = postprocess_stt_text(text) if result.is_final else text
                    self._emit_result(processed, result.is_final)

        except Exception as e:
            self._emit_error(f"{type(e).__name__}: {e}")