# 검증 결과

2026년 11월 18일 로컬 SQLite, FastAPI, Vue SSR 빌드, Chromium에서 확인했다. 기존 사용자의 데이터에 영향을 주지 않도록 검증 서버는 임시 데이터베이스를 사용했다.

## 대표 시나리오

실제 외부 API가 반환한 3페이지의 후보와 상세·참고자료를 고정하고, 같은 대화 API에서 아래 요청을 실행했다. 날짜는 2026-11-18, 시작은 14:00, 언어는 Python이다. 부분 실패 사례만 참고자료 응답을 연결 실패로 대체했다. 각 사례의 요청 원문, 최종 답변, 호출 도구와 순서, 실행 단계, 재계획 횟수 및 처리 시간을 저장했다. [실측 원본](evidence/live-tools.json) · [시나리오별 결과](evidence/scenarios.json)

| 요청·상태 | 기대한 동작 | 실제 결과 |
|---|---|---|
| 15:00까지 계획 | 첫 페이지에서 추천 | 2,115자 이슈 #445를 14:00~14:13으로 제안했다. 마감 기준 가장 늦은 시작은 14:47이었다. |
| 같은 대화에서 “종료만 14시 10분으로” | 날짜·언어·시작 유지, 마감만 갱신 | 두 번째 페이지에서 #443을 추천했다. 날짜와 시작 시각이 유지됐다. |
| 14:10까지 계획 | 첫 후보 탈락 후 다음 페이지 탐색 | 첫 페이지의 16분·13분 후보를 제외하고 578자 이슈 #443을 7분 일정으로 제안했다. 참고 질문은 한 번 조회했다. [전체 실행 로그](evidence/replan-run.json) |
| 14:02까지 계획 | 재계획 2회에서 정지 | 3페이지까지 확인하고 상한 도달 이유와 조건 변경 안내를 반환했다. |
| 참고자료 제공기관 연결 실패 | 실패를 표시하고 이슈 검토 일정 제안 | 참고자료는 UNAVAILABLE로 표시하고 13분 일정을 제안했다. |
| 사용법 요청 | 도구 호출 없이 안내 | 도구 호출 0회, 날짜·시간·언어를 포함한 입력 예시를 반환했다. |
| 모델 키가 없는 상태에서 모호한 요청 | 오류 상세 노출 없이 입력 방법 안내 | 도구 호출 0회, 모델 키 설정 또는 조건 직접 입력을 안내했다. |
| 언어만 지정 | 날짜·시각을 임의로 정하지 않고 확인 | 도구 호출 0회, 날짜·시작·마감 입력을 요청했다. |

점검 중 “종료만 14시 10분으로”가 시작 시각 갱신으로 해석되는 경우를 발견해 조사 ‘만’을 포함한 종료·마감 표현을 수정했다. 수정 뒤 세 가지 시각 변경 표현을 회귀 검사했고, 같은 세션에서 실제 API 응답의 조건 네 개도 대조했다. [Agent 회귀 테스트](../backend/test/test_planner_agent.py)

## 실서비스 호출과 처리 시간

GitHub Search, GitHub Issues, Stack Exchange를 사용하는 요청으로 실제 외부 연결을 확인했다. 60분 가용 조건에서 후보 검색 한 번, 상세 조회 두 번, 참고자료 검색 한 번을 거쳐 추천이 반환됐다. 환경·시각에 따라 GitHub의 최신 후보와 응답 시간은 달라진다. 전체 요청 시간은 JSON의 `elapsed_ms`, 각 도구의 소요 시간은 해당 `tool_response`에 있다. 비교용 성능 기준은 이 환경에서 정상 대표 요청 5초 이내로 정했다. [실제 요청과 전체 로그](evidence/live-request.json)

자유 형식 의도 분류도 실제 GMS 모델에 등록 도구 정보를 전달해 확인했다. 이전 조건이 Python인 대화에서 모델이 `search_resources`를 선택했으며 선택 사유와 인자가 남았다. [실제 모델 선택](evidence/live-model-selection.json)

## 항목별 증빙

| 검증 항목 | 증빙 |
|---|---|
| 4.1 등록 스키마, 기본 조회일·조회일 차이, 실패·빈 결과·미확인 속성 | [등록 화면](evidence/tools.png) · [정상·실패 결과](evidence/tool-contracts.json) · [도구 테스트](../backend/test/test_planner_tools.py) |
| 4.2 실행 그래프, 근거 계산, 재계획 상한, 맥락 유지 | [컴파일된 그래프 출력](evidence/graph.mmd) · [추천 화면](evidence/chat.png) · [재계획 지점](evidence/replan.png) · [상한 도달](evidence/limit.png) |
| 4.3 원본 이벤트, 순서, 세션 분리, 목록·상세·삭제·수정 불가, 구독자 실패 격리 | [세션 상세 화면](evidence/logs.png) · [저장소·API 테스트](../backend/test/test_planner_api.py) · [전체 로그](evidence/replan-run.json) |
| 4.4 계획 저장·상세·수정·삭제, 겹치는 계획의 저장과 경고 | [수정·겹침 안내 화면](evidence/plans.png) · [브라우저 검증 코드](../frontend/test/planner-browser.mjs) |
| 4.5 FastAPI 문서, API 기반 화면, 처리 중과 오류 안내 | [Swagger UI](evidence/api.png) · [처리 중](evidence/pending.png) · [모바일 부분 실패](evidence/partial-mobile.png) · [모델 키 누락](evidence/missing-key.png) |
| 4.6 심화 기능 | 이번 제출의 선택 범위는 기본 기능이다. |
| 4.7~4.9 대표 요청, 비기능 요구사항, 제출물 | [시나리오별 결과](evidence/scenarios.json) · [자체 체크리스트](checklist.md) |

## 재현 방법

1. 백엔드에서 `uv sync --locked` 후 `uv run --locked python -m unittest discover -s test -v`를 실행한다. 26건 중 25건이 통과했다. 기존 이력서 원본을 외부 파싱 서비스로 보내는 선택 검사는 `RUN_RESUME_LIVE`를 사용하지 않아 1건 건너뛰었다. 플래너 검사 20건은 모두 실행했다.
2. 백엔드에서 `uv run --locked python scripts/verify_submission.py`를 실행하면 임시 DB에서 실측 데이터를 재생하고 결과 파일을 갱신한다. `--live`를 붙이면 현재 공개 API를 호출한 결과도 기록한다.
3. 화면 검증은 백엔드에서 `uv run --locked python scripts/verify_submission.py --serve 18143`으로 빈 임시 DB를 시작한다. 프런트엔드에서 `npm ci && npm run build` 후 `PLANNER_BACKEND_URL=http://127.0.0.1:18143 npm run preview -- --port 15174`를 실행한다.
4. Chromium과 Playwright가 설치된 환경에서 저장소 루트 기준 `PLANNER_UI_URL=http://127.0.0.1:15174 node frontend/test/planner-browser.mjs`를 실행한다. 별도 설치한 Playwright 모듈이나 브라우저를 쓰는 경우 `PLAYWRIGHT_MODULE`과 `CHROMIUM_PATH`에 해당 경로를 지정한다. 테스트는 홈 진입부터 실제 HTTP 요청, 일정 CRUD, 로그 삭제, 새로고침 복원, 모바일 화면까지 점검한다.
