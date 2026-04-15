# Log Assistant Backend

Minimal FastAPI backend scaffold for an intelligent log analysis assistant. The project is intentionally simple: endpoints return placeholder responses, while PostgreSQL and Redis are included in Docker Compose for future persistence and background work.

## Structure

```text
app/
  api/
  core/
  models/
  schemas/
  services/
tests/
```

## Endpoints

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `POST /logs/upload`
- `GET /logs`
- `GET /logs/{id}`
- `POST /logs/{id}/analyze`

## Run with Docker Compose

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`, and interactive docs at `http://localhost:8000/docs`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## Notes

- Business logic is intentionally mocked for easy walkthroughs in interviews.
- `app/core/config.py` centralizes environment-based settings.
- PostgreSQL and Redis are wired in as infrastructure placeholders, not yet active dependencies in request handling.
