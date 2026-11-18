# 제출 전 자체 체크리스트

별도 배포된 셀프 체크리스트가 없어 요구사항정의서 4.1~4.9와 6장을 기준으로 작성했다. 점검일은 2026년 11월 18일이다.

| 항목 | 점검 결과 | 근거 |
|---|---|---|
| F3001~F3004 | 통과 · 등록 스키마, 정상·실패 반환, 후보→상세 식별자, 조회일 차이, 참고자료, 빈 결과 및 분량 누락 | [계약 표본](evidence/tool-contracts.json), [실제 외부 호출](evidence/live-tools.json) |
| F3005~F3011 | 통과 · 요청 분석, 조건별 도구 선택, 그래프 실행, 분량 비교, 상한 종료, 후속 요청, 근거·제외 사유 | [그래프](evidence/graph.mmd), [실행 기록](evidence/replan-run.json), [모델 도구 선택](evidence/live-model-selection.json) |
| F3012~F3014 | 통과 · 단계·도구·판단 이벤트, LLM 없는 구독 및 저장, 세션 격리, 로그 상세·삭제, 수정 요청 405 | [실행 기록](evidence/live-request.json), [API 검증](../backend/test/test_planner_api.py) |
| F3015~F3016 | 통과 · 같은 날짜의 시간 중복을 허용하고 알림, 날짜·시간·제목 수정, 생성 일시 유지, 삭제 후 목록 갱신 | [계획 관리](evidence/plans.png), [브라우저 검사](../frontend/test/planner-browser.mjs) |
| F3017~F3019 | 통과 · 대화·계획·로그 경로 분리, Vue 연동, 처리 상태, 도구 이력·재계획·오류 표시 | [API](evidence/api.png), [진행 중](evidence/pending.png), [재계획](evidence/replan.png), [키 설정 안내](evidence/missing-key.png) |
| NF3001~NF3002 | 통과 · 서버 환경변수 사용, 제출 대상에서 로컬 키 파일 제외, 오류 시 제공기관 응답을 안전한 메시지로 변환 | [도구 실패 검사](../backend/test/test_planner_tools.py), [오류 화면](evidence/partial-mobile.png) |
| NF3003~NF3004 | 통과 · 보조 도구 실패 후 일정 생성, 상한 2회에서 종료 | [부분 실패·상한 사례](evidence/scenarios.json) |
| NF3005 | 통과 · 공개 API를 호출한 정상 요청이 로컬 점검 기준 5초 이내에 완료 | [실측 소요 시간](evidence/live-request.json) |
| NF3006 | 통과 · Vue 프런트와 FastAPI 백엔드 분리, 그래프·도구·로깅 모듈 분리 | [프런트](../frontend/src/components/planner), [백엔드](../backend/app) |
| NF3007 | 확인 · 제공기관별 출처·한도·이용 조건 기록, 응답에 원문·저작자·라이선스 표시 | [Tool 정의서](tools.md), [추천 화면](evidence/chat.png) |
| 검증 자료 | 대표 요청 8건의 결과, 실제 외부 요청, 실측 데이터 재생, 재계획 전체 로그, 화면 첨부 | [검증 결과](verification.md) |
| 제출 자료 | 요구사항·Agent·Tool·API 명세, 검증서, 체크리스트, 소스, 실행 방법 및 API 키 설정 안내 | [제출 자료 목록](../README.md) |
| 심화 비교 | 선택한 심화 과제 없음 | [요구사항 범위](requirements.md) |

명세 1.2의 필수 패키지 17종은 지정한 버전을 프로젝트 의존성과 잠금 파일에 명시했다. [프로젝트 의존성](../backend/pyproject.toml) · [잠금 파일](../backend/uv.lock)
