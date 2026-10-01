# Checkpoint — job-712c231c-e993-4a63-b844-c3f6a59cd63e (Flask LMS API)

## Stack decisions (STEP 1)
- Python 3.13.5, Flask 3.1.0, raw SQL via PyMySQL (no ORM), bcrypt, PyJWT, gunicorn (Linux)/waitress (Windows).
- MySQL 8.4.3, container port 3306, app listens 0.0.0.0:8000.
- Swagger UI hand-written per capabilities/reports-and-deploy.md (no OpenAPI lib): `openapi_spec.py` dict, served at `/openapi.json`; `/docs` HTML loads swagger-ui-dist from CDN.
- Error envelope: `{error, code, timestamp, correlation_id}` via `errors.py` custom exception hierarchy + centralized Flask error handlers in `app.py`. Correlation ID read from `X-Request-ID`/`X-Correlation-ID` header else generated (uuid4), set into `flask.g.correlation_id`.
- Logging: stdlib `logging`, module-level `logger = logging.getLogger(__name__)`, correlation id in every log line, no secrets/PII logged.

## File layout
```
app.py, config.py, db.py, auth.py, errors.py, openapi_spec.py, wsgi.py
requirements.txt, schema.sql, .env, .env.example, Dockerfile, docker-compose.yml, start.sh, start.bat, README.md
models/ {user,course,module,lesson,enrollment,certificate,progress}_model.py
routes/ {auth,course,module,lesson,enrollment,progress,certificate}_routes.py, docs_routes.py (health/docs/openapi.json)
tests-artifacts/ (reports, written later)
```

## Shared contracts (pinned here, handed verbatim to subagents)
- `db.py`: `get_connection()` (PyMySQL conn, DictCursor, autocommit=True), `execute(sql, params=())->int` (lastrowid or affected rows), `query_one(sql, params=())->dict|None`, `query_all(sql, params=())->list[dict]`. All open/close connection per call, log operation + affected rows at DEBUG/INFO, never log params that contain secrets.
- `auth.py`: `hash_password(password)->str`, `verify_password(password, hashed)->bool`, `generate_token(user_id, role)->str`, `decode_token(token)->dict|None`, `@login_required` (sets `flask.g.user_id`, `flask.g.role`; raises/returns 401 JSON via `AuthenticationError`), `@role_required(role)` (raises `UnauthorizedError` -> 403 if `flask.g.role != role`).
- `errors.py`: `AppError` base (status_code, code, message) with `ValidationError`(400), `AuthenticationError`(401), `UnauthorizedError`(403), `NotFoundError`(404), `ConflictError`(409), `DuplicateEnrollmentError(ConflictError)`(409). Routes raise these; `app.py` registers handlers converting to the envelope.
- Model function signatures: exactly as specified in the task prompt's "Wave 3/4" sections (user_model, course_model, module_model, lesson_model, enrollment_model, certificate_model, progress_model) — each service-builder task is given its exact subset verbatim.
- Route blueprints/paths: exactly as specified in task prompt's "Wave 5" section.
- Layering: routes (thin, validation+auth) -> models (treated as combined business+data layer per db.py helpers, cascade logic lives in `progress_model.upsert_lesson_progress`) -> db.py (raw SQL).

## Groups dispatched to service-builder (STEP 1 parallel dispatch)
| Group | Files | Status |
|---|---|---|
| G1 Auth | models/user_model.py, routes/auth_routes.py | pending |
| G2 Course | models/course_model.py, routes/course_routes.py | pending |
| G3 Module | models/module_model.py, routes/module_routes.py | pending |
| G4 Lesson | models/lesson_model.py, routes/lesson_routes.py | pending |
| G5 Enrollment | models/enrollment_model.py, routes/enrollment_routes.py | pending |
| G6 Progress+Certificate | models/progress_model.py, models/certificate_model.py, routes/progress_routes.py, routes/certificate_routes.py | pending |

## Progress
- [x] STEP 1: design decisions, directory scaffold
- [ ] config.py, requirements.txt, schema.sql
- [ ] db.py, auth.py, errors.py
- [ ] models/routes (6 groups, parallel)
- [ ] app.py, openapi_spec.py, docs_routes.py, wsgi.py
- [ ] .env/.env.example, Dockerfile, docker-compose.yml, start.sh/start.bat, README.md
- [ ] syntax check
- [ ] boot verification + curl tests
- [ ] test report (xlsx + docx)
- [ ] final summary
