# Checkpoint — job-712c231c-e993-4a63-b844-c3f6a59cd63e (Flask LMS API)

## Stack decisions (STEP 1)
- Python 3.13.5, Flask 3.1.0, raw SQL via PyMySQL (no ORM), bcrypt, PyJWT, gunicorn (Linux)/waitress (Windows).
- MySQL 8.4.3 (docker-compose deliverable), container port 3306, app listens 0.0.0.0:8000.
- Swagger UI hand-written per capabilities/reports-and-deploy.md (no OpenAPI lib): `openapi_spec.py` dict, served at `/openapi.json`; `/docs` HTML loads swagger-ui-dist from CDN.
- Error envelope: `{error, code, timestamp, correlation_id}` via `errors.py` custom exception hierarchy + centralized Flask error handlers in `app.py`. Correlation ID read from `X-Request-ID`/`X-Correlation-ID` header else generated (uuid4), set into `flask.g.correlation_id`, echoed back in the response header and in every log line.

## Final file layout
```
app.py, config.py, db.py, auth.py, errors.py, openapi_spec.py, wsgi.py, apply_schema.py
requirements.txt, schema.sql, .env, .env.example, Dockerfile, docker-compose.yml, start.sh, start.bat, README.md
models/ {user,course,module,lesson,enrollment,certificate,progress}_model.py
routes/ {auth,course,module,lesson,enrollment,progress,certificate}_routes.py, docs_routes.py (health/docs/openapi.json)
tests-artifacts/ api_test_report.xlsx, project_report.docx
```

## Final contracts (ground truth — matches the task spec's Wave 3/4/5 sections exactly)
- `db.py`: `execute(sql, params=())->int`, `query_one(sql, params=())->dict|None`, `query_all(sql, params=())->list[dict]`.
- `auth.py`: `hash_password`, `verify_password`, `generate_token(user_id, role)`, `decode_token(token)`, `@login_required` (sets `g.user_id`/`g.role`), `@role_required(role)`.
- `errors.py`: `AppError` base + `ValidationError`(400), `AuthenticationError`(401), `UnauthorizedError`(403), `NotFoundError`(404), `ConflictError`(409), `DuplicateEnrollmentError(ConflictError)`(409).
- Blueprints (exact names used in `app.py`): `auth_bp`, `course_bp` ("courses"), `module_bp` ("modules"), `lesson_bp` ("lessons"), `enrollment_bp`, `progress_bp`, `certificate_bp`, `docs_bp`.
- Endpoints: exactly the 12 business endpoints + `/health`, `/docs`, `/openapi.json` listed in the task spec (see README.md's API summary table).

## Groups dispatched to service-builder (STEP 1 parallel dispatch) — outcome
| Group | Files | Outcome |
|---|---|---|
| G1 Auth | models/user_model.py, routes/auth_routes.py | Matched pinned contract as-is. |
| G2 Course | models/course_model.py, routes/course_routes.py | Mostly matched; main agent fixed: stats endpoint now returns a 0.0-1.0 fraction (not 0-100), `search_courses` now always annotates `enrolled` for students (not only when filtering). |
| G3 Module | models/module_model.py, routes/module_routes.py | Mostly matched; main agent added missing `list_module_ids_for_course` (subagent had only `count_modules_in_course`) and fixed `GET /courses/<id>/modules` to nest lessons per module (spec requirement, subagent had omitted it). |
| G4 Lesson | models/lesson_model.py, routes/lesson_routes.py | Matched pinned contract as-is. |
| G5 Enrollment | models/enrollment_model.py, routes/enrollment_routes.py | **Subagent ignored the pinned contract** (invented a generic `/enrollments` CRUD surface with different function/endpoint names). Main agent fully rewrote both files to the exact spec: `create_enrollment`, `get_enrollment`, `set_enrollment_status`, `count_enrollments`, `count_completed_enrollments`, `completion_rate`, and `POST /courses/<id>/enroll`. |
| G6 Progress+Certificate | models/progress_model.py, models/certificate_model.py, routes/progress_routes.py, routes/certificate_routes.py | **Subagent invented different blueprint names/endpoints/function names** (e.g. `issue_certificate` instead of `create_certificate`, `/certificates` instead of `/students/<id>/certificates`). Main agent fully rewrote all four files to the exact spec'd cascade logic and endpoints. |

Lesson learned: several subagents drifted from the exact pinned function/endpoint names even when given verbatim in the task prompt. Main agent did a full read-and-reconcile pass before wiring `app.py`, rewriting non-compliant files outright rather than patching around the drift, then verified every contract end-to-end with live curl tests (see below).

## Progress
- [x] STEP 1: design decisions, directory scaffold
- [x] config.py, requirements.txt, schema.sql
- [x] db.py, auth.py, errors.py
- [x] models/routes (6 groups dispatched in parallel + main-agent reconciliation fixes, see table above)
- [x] app.py (factory, centralized error handlers, correlation-id logging filter), openapi_spec.py, docs_routes.py (/health /docs /openapi.json), wsgi.py
- [x] .env / .env.example, Dockerfile, docker-compose.yml, start.sh / start.bat, README.md, apply_schema.py — `test -f Dockerfile && test -f docker-compose.yml` verified present
- [x] syntax check: `python -m py_compile` on every file — clean; `ruff check .` — all checks passed (fixed 2 logging-style nits + 1 unused import)
- [x] boot verification + curl tests — see note below on environment; full cascade verified end-to-end: register (instructor+student, 409 on dup email) → login (401 on bad creds) → create course (403 for student) → create module → create 2 lessons → get course detail (nested modules/lessons) → enroll (409 on re-enroll) → list courses w/ `enrolled` flag → PUT progress lesson 1 COMPLETED (`module_completed_now=false`) → PUT progress lesson 2 COMPLETED (`module_completed_now=true`, `course_completed_now=true`) → certificate auto-issued and retrievable → 403 cross-student certificate access, 200 for instructor → course stats (`completion_rate` 0.0-1.0 fraction) → 400 invalid status → 401 no token. All passed as expected.
- [x] test report (xlsx + docx) generated under `tests-artifacts/`
- [x] final summary

## Environment note (Docker unavailable in this sandbox)
`docker_pull`/`docker_exec`/`docker_compose` all failed here with "Cannot connect to the Docker daemon at unix:///var/run/docker.sock" (daemon not running in this sandbox) and the `docker` CLI present has no `compose` subcommand. Per the mandatory Docker deliverables rule, `Dockerfile` and `docker-compose.yml` were still written (and verified present on disk with `test -f`) — they are deliverables for whoever deploys the project, not this harness's own verification mechanism. For this job's own boot verification, `mariadb-server` (MySQL-wire-compatible) was installed natively on the host and the Flask app was run natively via `gunicorn` bound to `0.0.0.0:8000`, started/polled/killed by PID per the boot-verification contract. The report-generation script was run via the host's native `python` per this environment's instructions.
