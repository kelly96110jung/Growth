# MedExplain Backend

MedExplain은 환자와 보호자의 의료 이해도 향상을 위한 진료 대화 자동 요약 및 의학 용어 설명 앱입니다.

진료 중 의사와 환자의 대화를 녹음하면, 앱은 음성을 텍스트로 변환하고, 의료 용어와 수치 표현을 교정한 뒤, 환자가 이해하기 쉬운 요약 리포트를 제공합니다. 또한 어려운 의학 용어를 쉬운 말로 설명하고, 사용자가 진료 내용에 대해 추가 질문을 할 수 있도록 Q&A 기능을 제공합니다.

이 저장소는 MedExplain의 FastAPI 기반 백엔드 서버입니다.

---

## 주요 기능

* Flutter 앱에서 전송한 오디오 데이터 수신
* Google Cloud STT 기반 음성 텍스트 변환
* 의료 약어, 단위, 수치 표현 후처리
* 규칙 기반 STT 오류 교정
* Gemini 기반 STT 문맥 교정
* Gemini 기반 진료 내용 요약
* 의료 전문 용어 추출 및 쉬운 설명 생성
* 진료과 자동 추천
* 진료 내용 기반 Q&A 응답 생성
* 진료 기록 저장 및 조회 API 제공

---

## 기술 스택

* Python
* FastAPI
* WebSocket
* Google Cloud STT API
* Gemini API
* Pydantic

---

## 주요 모듈

| 모듈                      | 설명                          |
| ----------------------- | --------------------------- |
| stt_google_streaming.py | Google STT 연동 및 음성 전사 처리    |
| stt_corrector.py        | STT 결과 후처리 및 교정             |
| summarizer.py           | Gemini 기반 진료 요약 생성          |
| term_extractor.py       | 의료 용어 추출 및 쉬운 설명 생성         |
| question_analyzer.py    | 사용자 질문 분석 및 AI 답변 생성        |
| schemas.py              | Pydantic 기반 요청/응답 데이터 모델 정의 |

---

## 주요 API

| API              | 설명                     |
| ---------------- | ---------------------- |
| WebSocket        | 오디오 데이터 수신 및 STT 결과 반환 |
| POST /summary    | 진료 텍스트 요약              |
| POST /explain    | 의료 용어 추출 및 설명          |
| POST /department | 진료과 자동 추천              |
| POST /question   | 진료 내용 기반 Q&A           |
| POST /records    | 진료 기록 저장 및 조회          |

---

## 실행 방법

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

서버가 실행되면 Flutter 앱에서 설정한 서버 주소를 통해 WebSocket 및 REST API 요청을 받을 수 있습니다.

---

## 환경 변수 설정

본 프로젝트는 Gemini API와 Google Cloud STT API를 사용하므로 실행 전 환경 변수 설정이 필요합니다.

```bash
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=your_google_credentials_path
```

API Key와 인증 파일은 보안상 GitHub에 업로드하지 않습니다.

---

## 처리 흐름

1. Flutter 앱에서 오디오 데이터 전송
2. WebSocket으로 백엔드 서버가 오디오 수신
3. Google Cloud STT API를 통해 음성을 텍스트로 변환
4. 의료 약어, 단위, 소수점, 간투사 후처리
5. 규칙 기반 교정 및 Gemini 기반 문맥 교정 적용
6. 교정된 텍스트를 Flutter 앱으로 반환
7. `/summary`, `/explain`, `/question` 등의 API를 통해 AI 분석 결과 제공
8. 최종 진료 기록 저장 및 조회 지원

---

## 주의사항

MedExplain Backend는 환자와 보호자가 진료 내용을 쉽게 이해하도록 돕기 위한 분석 결과를 제공합니다.
AI 요약과 Q&A 답변은 참고용이며, 실제 진단, 처방 변경, 수술 여부 등 중요한 의료 판단은 반드시 담당 의료진의 판단을 따라야 합니다.
