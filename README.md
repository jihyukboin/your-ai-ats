# AI 코어 플래너

| 디렉터리 | 구성 |
|---|---|
| `frontend/` | Vue 3와 Vite |
| `backend/` | FastAPI와 Uvicorn |
| `infra/` | SQLite 로컬 데이터 파일 |

## 로컬 실행

Python 3.11 이상, uv, Node.js 20.19 이상인 20.x 또는 Node.js 22.12 이상이 필요합니다.

프로젝트 루트에서 터미널 두 개를 열어 각각 실행합니다.

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

- 프론트엔드 화면은 `http://127.0.0.1:5173`에서 열립니다. Vite가 `/api` 요청을 FastAPI로 전달합니다.
- API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.
- `GET /api/health`는 SQLite 조회가 성공하면 HTTP 200과 `{"status":"ok","database":"sqlite"}`를 반환합니다.
- 프론트엔드 빌드는 `frontend/`에서 `npm run build`로 실행합니다.
