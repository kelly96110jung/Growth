# MedExplain Backend

## 1. Project Description

MedExplain은 환자와 보호자의 의료 이해도 향상을 위한 진료 대화 자동 요약 및 의학 용어 설명 앱입니다.

진료 중 의사와 환자의 대화를 녹음하면, 앱은 음성을 텍스트로 변환하고, 의료 용어와 수치 표현을 교정한 뒤, 환자가 이해하기 쉬운 요약 리포트를 제공합니다. 또한 어려운 의학 용어를 쉬운 말로 설명하고, 사용자가 진료 내용에 대해 추가 질문을 할 수 있도록 Q&A 기능을 제공합니다.

본 저장소는 MedExplain의 FastAPI 기반 Backend source code를 포함합니다.

---

## 2. Source Code Description

Backend는 Flutter 앱에서 전달한 음성 및 텍스트 데이터를 처리하고, Google STT API와 Gemini API를 연동하여 AI 분석 결과를 생성합니다.

주요 기능은 다음과 같습니다.

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

주요 모듈은 다음과 같습니다.

| Module                  | Description                 |
| ----------------------- | --------------------------- |
| stt_google_streaming.py | Google STT 연동 및 음성 전사 처리    |
| stt_corrector.py        | STT 결과 후처리 및 교정             |
| summarizer.py           | Gemini 기반 진료 요약 생성          |
| term_extractor.py       | 의료 용어 추출 및 쉬운 설명 생성         |
| question_analyzer.py    | 사용자 질문 분석 및 AI 답변 생성        |
| schemas.py              | Pydantic 기반 요청/응답 데이터 모델 정의 |

---

## 3. Tech Stack

* Python
* FastAPI
* WebSocket
* Google Cloud STT API
* Gemini API
* Pydantic

---

## 4. How to Install

Python 가상환경을 생성합니다.

```bash
python -m venv venv
```

가상환경을 활성화합니다.

Windows:

```bash
venv\Scripts\activate
```

macOS / Linux:

```bash
source venv/bin/activate
```

필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

---

## 5. Environment Variables

Backend 실행 전 Google STT API와 Gemini API 사용을 위한 환경 변수 설정이 필요합니다.

```bash
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=your_google_credentials_path
```

API Key와 인증 파일은 보안상 GitHub에 업로드하지 않습니다.

---

## 6. How to Run

FastAPI 서버를 실행합니다.

```bash
uvicorn main:app --reload
```

서버가 실행되면 Flutter 앱에서 설정한 서버 주소를 통해 WebSocket 및 REST API 요청을 받을 수 있습니다.

---

## 7. How to Build

Backend는 Python 기반 FastAPI 서버이므로 별도의 빌드 과정은 필요하지 않습니다.

배포 환경에서는 필요한 패키지를 설치한 뒤 ASGI 서버로 실행할 수 있습니다.

예시:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 8. How to Test

서버 실행 후 다음 API를 호출하여 기능을 확인할 수 있습니다.

| API              | Description            |
| ---------------- | ---------------------- |
| WebSocket        | 오디오 데이터 수신 및 STT 결과 반환 |
| POST /summary    | 진료 텍스트 요약              |
| POST /explain    | 의료 용어 추출 및 설명          |
| POST /department | 진료과 자동 추천              |
| POST /question   | 진료 내용 기반 Q&A           |
| POST /records    | 진료 기록 저장 및 조회          |

예시 요청:

```json
{
  "text": "CRP 수치가 조금 올라서 염증 상태를 더 지켜봐야 합니다. 내일 CBC 검사를 다시 진행하고, 약은 5mg으로 조절하겠습니다."
}
```

기대 결과:

* `/summary`에서 핵심 진료 내용 요약 반환
* `/explain`에서 CRP, CBC, 5mg 등 의료 용어 및 수치 설명 반환
* `/question`에서 진료 원문 기반 답변 반환

---

## 9. Sample Data

테스트용 sample/proto data 예시는 다음과 같습니다.

```text
CRP 수치가 조금 올라서 염증 상태를 더 지켜봐야 합니다.
내일 CBC 검사를 다시 진행하고, 약은 5mg으로 조절하겠습니다.
MRI를 찍어보는 것이 좋을 것 같고, L4-L5 디스크도 확인되었습니다.
```

예상 처리 결과:

* `CRP` → 염증 수치로 설명
* `CBC` → 혈액 검사로 설명
* `5mg` → 약물 용량으로 인식
* `MRI` → 영상 검사로 설명
* `L4-L5` → 척추 레벨 표현으로 교정 및 유지

---

## 10. Open Source / External APIs

본 Backend는 다음 외부 API 및 라이브러리를 사용합니다.

| Library / API        | Purpose                      |
| -------------------- | ---------------------------- |
| FastAPI              | Backend API 서버 구현            |
| Pydantic             | 요청 및 응답 데이터 모델 정의            |
| Google Cloud STT API | 음성 텍스트 변환                    |
| Gemini API           | STT 교정, 진료 요약, 용어 설명, Q&A 생성 |

---

## 11. Notes

MedExplain Backend는 환자와 보호자가 진료 내용을 쉽게 이해하도록 돕기 위한 분석 결과를 제공합니다.

AI 요약과 Q&A 답변은 참고용이며, 실제 진단, 처방 변경, 수술 여부 등 중요한 의료 판단은 반드시 담당 의료진의 판단을 따라야 합니다.
