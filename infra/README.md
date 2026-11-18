# SQLite

FastAPI가 시작될 때 `infra/data/planner.sqlite3`를 생성합니다. 백엔드는 Python 표준 라이브러리의 `sqlite3` 모듈로 이 파일에 접근합니다. 데이터 파일은 Git 추적 대상에서 제외합니다.
