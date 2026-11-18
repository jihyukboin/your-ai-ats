# 개발 포트폴리오 플래너 Tool 정의서

사용자가 선택한 언어로 입문용 오픈소스 이슈를 찾고, 원문을 검토할 시간을 일정에 배정한다. 검색 결과가 주는 식별자, 이슈 원문에서 잰 글자 수, 별도 사이트의 학습 자료를 조합한다. API가 제공하는 글자 수로 **본문 검토**를 계획하며 구현·테스트·PR 완료 시간은 알 수 없다.

## 등록과 호출 계약

세 도구는 외부 API 도구다. 서버의 계획 저장·수정은 사용자의 확정 동작으로 실행한다. 등록한 이름, 도구를 선택할 상황, 입력과 성공·실패 출력 JSON Schema는 `GET /api/planner/tools`에서 확인한다. [등록부](../backend/app/planner_tools.py) · [실행 시 출력한 스키마](evidence/tool-contracts.json)

| 이름과 사용 시점 | 입력 | 성공 시 `data` |
|---|---|---|
| `search_candidates` · 새 후보나 다음 페이지의 대안이 필요할 때 | `language` 언어명, `page` 1~500(기본 1), `reference_date` 조회 기준일(기본 서울 오늘) | `items[]`에 `id, name, url`. 페이지당 최대 두 건. `page, has_more, requested_date, observed_date, note` |
| `candidate_detail` · 후보별 읽기 분량을 판단할 때 | 후보 목록에서 받은 `id` 한 개. 형식은 `owner/repository#번호` | `id, name, url, body_chars, comments, labels`. 본문이 없으면 길이는 null, 댓글 수가 제공되지 않으면 null |
| `search_resources` · 선호 언어의 학습 자료를 함께 보여줄 때 | `language` 언어명 | `items[]`에 질문 제목 `name`, 원문 `url`, 작성자 `author`, 프로필 `author_url`, 적용 라이선스 `license`. 언어 태그별 상위 질문 최대 두 건 |

후보 API는 생성일 내림차순으로 공개·열림·입문 라벨 이슈를 검색한다. 조회 기준일과 실제 조회일이 다르면 현재 상태로 조회했다는 설명을 `note`로 돌려준다. 일정 날짜와 데이터 조회일은 별개다. 상세 API는 검색에서 받은 저장소와 번호로 다시 조회하여 닫힌 이슈, PR, 입문 라벨이 제거된 이슈를 제외한다. `body_chars`는 마크다운 본문 양끝 공백을 제거한 뒤 센 문자 수다. 참고 질문은 언어 태그로 검색한다.

모든 호출은 `{"ok": true, "data": …}` 또는 `{"ok": false, "error": {"code": "…", "message": "…"}}`를 반환한다. 예외 응답의 본문·URL·헤더는 사용자에게 전달하지 않는다.

| 코드 | 발생 조건 |
|---|---|
| `INVALID_INPUT`, `UNKNOWN_TOOL` | 명세에 없는 인자, 형식·범위 위반, 미등록 도구 |
| `NO_RESULT`, `NOT_FOUND` | 후보·보조 자료가 없거나 상세가 입문 이슈 조건을 벗어남. 원본이 삭제·비공개이면 404를 `NOT_FOUND`로 변환 |
| `AUTH_ERROR`, `RATE_LIMIT` | 제공자 인증 또는 권한 문제, 공급자 호출 제한 또는 대기 중 |
| `UNAVAILABLE`, `UPSTREAM_ERROR`, `INVALID_RESPONSE` | 접속 실패·타임아웃, 제공기관 HTTP 오류, 예상 형식과 다른 응답 |

도구를 추가할 때는 `Input`을 상속한 인자 모델과 결과 모델, 비동기 조회 함수를 작성하고 `REGISTRY`에 이름과 선택 조건을 등록한다. `invoke_tool`이 입력 검증과 공통 응답 처리를 맡는다. 계획에서 호출할 위치와 선행 결과의 인자 연결은 Agent에도 반영한다. 필수 도구에는 모델이 입력할 수 있는 임의 URL 인자가 없다.

## API 출처와 이용 조건

| 출처 | 자격·한도 및 사용 조건 |
|---|---|
| GitHub REST Search Issues | 공개 데이터는 키 없이 IP당 분당 검색 10회, 일반 인증 사용자는 분당 30회. 검색당 최대 1,000건이며 본 서비스는 두 건씩 조회한다. 공개 이슈의 제목·식별자와 원문 링크를 제공한다. [검색 API](https://docs.github.com/en/rest/search/search) · [GitHub 서비스 약관](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |
| GitHub REST Issues | 공개 조회 기본 IP당 시간당 60회, 일반 사용자 토큰은 시간당 5,000회. 응답의 잔여량·리셋 시각과 제한 응답을 처리한다. 실제 할당량에는 자격별 차이가 있다. 이슈 본문은 분량 계산 후 버리고 저장소·이슈 링크를 남긴다. [이슈 API](https://docs.github.com/en/rest/issues/issues) · [한도](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) |
| Stack Exchange API v2.3 · Stack Overflow | 키 없이 제공되는 일일 할당량은 실측 응답에서 300회. 제공자가 응답으로 알리는 일시 대기(`backoff`)를 적용하며 동일 태그를 60초간 캐시한다. 질문 제목과 원문·작성자·라이선스 정보를 함께 전달한다. [질문 API](https://api.stackexchange.com/docs/questions) · [한도](https://api.stackexchange.com/docs/throttle) · [API 약관](https://stackoverflow.com/legal/api-terms-of-use) · [콘텐츠 라이선스](https://stackoverflow.com/help/licensing) |

필수 세 도구의 기본 경로는 키 발급 없이 재현할 수 있다. 검색량이 많은 환경에서는 GitHub의 **공개 저장소 읽기 전용** 토큰을 서버의 `PLANNER_GITHUB_TOKEN`에 설정할 수 있다. 이 토큰은 GitHub 요청의 인증 헤더에만 쓴다. [GitHub 토큰 발급 안내](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

### 기업 분석·이력서 기능에서 사용하는 별도 API

| 출처 | 용도·이용 조건 |
|---|---|
| 공공데이터포털 · 금융위원회, 한국산업인력공단 | 기업기본정보와 NCS 기준정보. 각각 활용 신청 후 승인된 서비스키를 서버 `DATA_GO_KR_API_KEY`에 설정한다. 각 데이터 상세 페이지의 개발계정 신청 가능 트래픽 10,000, 운영계정 증량은 활용 사례 등록 후 신청한다. 두 데이터 모두 이용허락범위 제한 없음으로 표시되어 있다. [금융위 원본](https://www.data.go.kr/data/15043184/openapi.do) · [NCS 원본](https://www.data.go.kr/data/15128213/openapi.do) |
| 금융감독원 Open DART | 기업개황·공시목록. 인증키 신청 후 서버 `DART_API_KEY`에 설정한다. 요청 제한 초과 코드 020의 일반 기준은 20,000건이며 개별 설정이 우선한다. 전자공시 원문 링크를 근거로 제공한다. [개발 가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019002) · [이용약관](https://opendart.fss.or.kr/intro/terms.do) |
| OpenAI Responses, SSAFY GMS | 기업 분석 보완 검색은 서버 `OPENAI_API_KEY`, SSAFY용 모델 호출은 `GMS_API_KEY`를 사용한다. 계정·모델별 요청 및 토큰 한도가 적용되며 GMS는 교육 계정의 승인 크레딧·유효기간을 따른다. [OpenAI 한도](https://developers.openai.com/api/docs/guides/rate-limits) · [서비스 약관](https://openai.com/policies/services-agreement/) · [GMS 키 발급](https://gms.ssafy.io/web/) |
| Upstage Document Parse | 이력서 문서 파싱. 계정의 API 키, 사용량 및 요금은 Upstage Console에서 관리하며 계약·상품별 사용 조건을 따른다. [개발자 콘솔](https://console.upstage.ai/) · [서비스 약관](https://www.upstage.ai/terms-of-service/update-may-06-2026) |

## 기획 검증과 설계 반영

2026-11-18 공개 API에 연결해 Python 이슈 검색 3페이지, 해당 식별자 6건의 상세, 별도 출처의 Python 참고 질문을 조회했다. 호출 인자·결과·수집 시각을 저장했다. [실제 API 결과](evidence/live-tools.json)

| 확인한 내용 | 설계 반영 |
|---|---|
| GitHub 검색의 저장소 API 주소와 이슈 번호로 상세 조회가 이어진다. 첫 번째 후보의 본문 3,230자와 댓글 0개를 확인했다. | 두 값을 조합한 안정적인 식별자를 사용한다. 검색 순번과 화면의 제목에 의존하지 않는다. |
| Python 첫 페이지 두 건은 3,230자·2,115자, 둘째 페이지에는 578자 항목이 있었다. | 사용자가 정한 시간에 맞지 않으면 언어를 유지한 채 다음 페이지에서 짧은 본문을 다시 찾는다. |
| 원문에는 이슈 해결 소요 시간이 없다. 본문이 비어 있는 응답에서도 검토 시간을 입증할 수 없다. | 실제 분량으로 본문 검토만 산정하며 빈 본문은 판단 보류한다. 폴백 숫자 삽입을 테스트로 방지한다. |
| 후보를 미래 기준일로 조회하면 현재 열린 목록만 얻을 수 있다. 없는 이슈 번호는 HTTP 404, 없는 Stack Overflow 태그는 빈 목록이다. | 조회일 차이를 표시하고 404·빈 목록을 명시적 실패로 변환한다. [도구별 정상·실패 표본](evidence/tool-contracts.json) |
| Stack Overflow 질문에는 질문 제목과 원문 URL, 작성자·라이선스 정보가 있다. | 프로젝트 이슈와 별개의 언어 학습 자료로 제공한다. 질문 본문과 답변 전체는 수집하지 않는다. |

실패를 안정적으로 재현하기 위해 공급자 거절, 연속 호출 제한, 상태 변경, 본문 누락은 HTTP 모의 응답으로 별도 검사했다. `cd backend && uv run --locked python -m unittest discover -s test -p test_planner_tools.py -v`로 일곱 검사를 재실행할 수 있다. [테스트 코드](../backend/test/test_planner_tools.py)
