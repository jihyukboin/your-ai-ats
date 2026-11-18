# Your ATS · AI 코어 플래너

개발 직무 지원자가 정해진 시간에 읽고 메모할 수 있는 오픈소스 이슈를 찾는 서비스입니다. 프로그래밍 언어와 가능한 시간을 입력하면 GitHub 후보를 조회하고 읽기 시간을 계산합니다. 적합한 후보가 없으면 다음 페이지를 탐색합니다. 추천 일정을 저장·수정하고 대화별 실행 로그를 확인할 수 있습니다.

## 실행

Python 3.11 이상과 uv, Node.js 20.19 이상(20.x) 또는 22.12 이상을 준비합니다. 저장소 루트에서 터미널 두 개로 실행합니다.

```bash
cd backend
uv sync --locked
uv run --locked uvicorn app.main:app --reload
```

```bash
cd frontend
npm ci
npm run dev
```

[플래너 화면](http://127.0.0.1:5173/workspace/planner)에서 “내일 14:00부터 15:00까지 Python 이슈 읽기 계획을 짜줘”를 전송합니다. 같은 대화에서 종료 시각만 바꿔 보거나, ‘계획 저장’ 후 ‘저장한 계획’에서 시각을 수정할 수 있습니다. [홈](http://127.0.0.1:5173)에서는 기존 이력서·기업 분석 기능을 이용합니다. 서버 상태는 [health](http://127.0.0.1:8000/api/health), API 스키마는 [FastAPI 문서](http://127.0.0.1:8000/docs)에서 확인합니다.

## 설정과 데이터

- 플래너의 이슈 검색·상세 조회와 Stack Overflow 질문 조회는 공개 API로 실행합니다. GitHub 인증이 필요한 경우 GitHub 계정의 Developer settings에서 공개 저장소 읽기용 토큰을 발급받아 백엔드 환경변수 `PLANNER_GITHUB_TOKEN`으로 설정합니다. [제공기관별 호출 한도·약관](docs/tools.md)
- 규칙으로 해석하기 어려운 플래너 요청에는 GMS 또는 OpenAI 모델을 사용합니다. 서버에 `GMS_API_KEY` 또는 `OPENAI_API_KEY`를 설정합니다. 등록된 예시처럼 조건이 분명한 요청은 모델 키 없이 실행됩니다.
- 기존 이력서·기업 분석 기능의 유료 모델 및 공공데이터 키는 `backend/.env`에서 설정합니다. GMS는 SSAFY GMS의 ‘Key 발급 신청’에서 발급하고, OpenAI는 프로젝트 API 키, 공공데이터는 공공데이터포털 활용 신청, DART는 OpenDART 인증키 신청, 이력서 OCR은 Upstage Console의 API Keys 메뉴를 이용합니다. 변수명은 `GMS_API_KEY`, `OPENAI_API_KEY`, `DATA_GO_KR_API_KEY`, `DART_API_KEY`, `UPSTAGE_API_KEY`입니다. 실제 키와 업로드한 이력서는 제출물에서 제외합니다.
- Vue 화면과 FastAPI는 분리되어 있습니다. SQLite는 실행 시 `infra/data/planner.sqlite3`에 자동 생성됩니다. 프런트엔드의 API 프록시는 기본적으로 `127.0.0.1:8000`을 사용하며 `PLANNER_BACKEND_URL`로 변경할 수 있습니다.
- 프런트엔드 빌드는 `frontend`에서 `npm run build`, 백엔드 회귀 검사는 `backend`에서 `uv run --locked python -m unittest discover -s test`로 실행합니다.

## 제출 자료

| 자료 | 내용 |
|---|---|
| [요구사항 정의서](docs/requirements.md) | 도메인 선정 근거, 필수 F3001~F3019, 비기능 NF3001~NF3007, 선택 범위 |
| [Agent 설계서](docs/agent.md) | LangGraph 실행 단계, 조건 판정, 재계획, 세션 기억과 이벤트 |
| [Tool 정의서](docs/tools.md) | 외부 API 계약, 실패 코드, 실호출 검증과 출처·이용 조건 |
| [API 명세서](docs/api.md) | 대화·계획·로그의 요청·응답 및 오류 |
| [검증 결과](docs/verification.md) | 대표 요청, 기대·실제 결과, 실행 로그와 화면 |
| [자체 체크리스트](docs/checklist.md) | 명세 4장 기준의 항목별 점검 결과 |
| 구현 소스 | [FastAPI](backend/app), [Vue](frontend/src), [회귀 테스트](backend/test) |

필수 기능은 포트폴리오 준비 플래너에서 확인합니다. 이번 회차에서 선택한 심화 기능은 없습니다.
