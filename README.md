# LMS REST API (Flask 3.1.0)

A Learning Management System REST API: instructors create courses/modules/lessons;
students enroll, track lesson progress, and automatically earn certificates when
every module in a course is completed.

## Stack

- Python 3.13.5, Flask 3.1.0
- MySQL 8.4.3 via raw SQL (PyMySQL, no ORM)
- JWT bearer auth (PyJWT) + bcrypt password hashing
- gunicorn (Linux) / waitress (Windows)
- Hand-written OpenAPI 3.0 spec served at `/openapi.json`; Swagger UI at `/docs`

## Running locally with Docker (recommended)

```bash
docker compose up -d --build
curl http://localhost:8000/health
open http://localhost:8000/docs
```

## Running natively

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # edit MYSQL_* to point at a running MySQL 8.4.3 instance
./start.sh             # start.bat on Windows
```

`start.sh`/`start.bat` apply `schema.sql` (idempotent `CREATE TABLE IF NOT EXISTS`)
before launching the WSGI server.

## Project layout

```
app.py              Flask application factory, blueprint registration, centralized error handling
config.py           Environment-driven configuration
db.py               Raw-SQL connection/query helpers (execute/query_one/query_all)
auth.py             Password hashing + JWT issue/validate + login_required/role_required decorators
errors.py           Domain exception hierarchy -> standard error envelope
openapi_spec.py     Hand-written OpenAPI 3.0 document
wsgi.py             WSGI entry point for gunicorn/waitress
apply_schema.py     One-off schema-apply helper run by start.sh/start.bat
schema.sql          MySQL DDL for all 7 tables
models/             Data-access (+ the progress/certificate cascade business logic)
routes/             Flask Blueprints (one per resource) — thin HTTP layer
tests-artifacts/    Generated test reports (xlsx + docx)
```

## API summary

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | /auth/register | public | |
| POST | /auth/login | public | |
| POST | /courses | instructor | |
| GET | /courses | any | `?category=`, `?enrollment_status=enrolled|not_enrolled` |
| GET | /courses/{id} | any | nested modules + lessons |
| GET | /courses/{id}/stats | instructor (owner) | |
| POST | /courses/{id}/modules | instructor (owner) | |
| GET | /courses/{id}/modules | any | nested lessons |
| POST | /modules/{id}/lessons | instructor (owner) | |
| POST | /courses/{id}/enroll | student | |
| PUT | /lessons/{id}/progress | student | cascades module/course completion + certificate issuance |
| GET | /students/{id}/certificates | self or instructor | |
| GET | /health | public | |
| GET | /docs | public | Swagger UI |
| GET | /openapi.json | public | OpenAPI 3.0 spec |

## Error envelope

Every error response has the shape:

```json
{"error": "message", "code": "ERROR_CODE", "timestamp": "2024-01-01T00:00:00+00:00", "correlation_id": "..."}
```
