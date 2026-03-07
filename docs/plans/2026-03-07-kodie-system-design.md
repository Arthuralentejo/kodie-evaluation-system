# Kodie Evaluation System Design (Approved)

## Architecture

- Monorepo layout:
  - `backend/` FastAPI app (Motor, JWT auth, middleware, routes, tests, index setup, rate-limit/lockout, revoke deny-list)
  - `frontend/` React + Vite scaffold (auth flow, questionnaire flow, autosave wiring)
  - `scripts/` ETL extraction (`extract.py`) and shared export helpers
  - `infra/` Render configs + env docs
- Backend structure:
  - `app/main.py` app bootstrap + exception handlers + request-id middleware
  - `app/core/` config, security (JWT), logging, errors
  - `app/db/` Motor client, collection accessors, index/migration bootstrap
  - `app/models/` Pydantic schemas/domain enums/validators (CPF check digits, option keys)
  - `app/services/` auth, assessments, answers, submission, rate-limit/revocation logic
  - `app/api/routes/` `auth`, `assessments`, `health`

## Data Flow and Behavior

### POST /auth
- Validate CPF format and check digits.
- Enforce per-CPF/per-IP rate limits and CPF lockout windows.
- Verify `cpf + birth_date` against `students`.
- Create/get one active `DRAFT` assessment with concurrency-safe upsert + duplicate-key retry.
- Issue JWT (`sub`, `assessment_id`, `iat`, `exp`, `jti`, `kid`) and return `assessment_id`.

### Auth middleware on /assessments/:id/*
- Validate JWT signature/expiry/claims.
- Check deny-list (`jti`) in DB; if unavailable, return `503` fail-closed.
- Enforce ownership: token `assessment_id` matches path and DB assessment `student_id == sub`.

### GET /assessments/:id/questions
- Fetch questions + saved answers.
- Apply deterministic option order using hash(`assessment_id`, `question_id`, `seed_version`).
- Return `selected_option` so reconnect restores prior state.

### PATCH /assessments/:id/answers
- Validate question exists and `selected_option` in canonical keys or `"DONT_KNOW"`.
- Upsert on (`assessment_id`, `question_id`), keep assessment in `DRAFT`.

### POST /assessments/:id/submit
- Compare answered question IDs vs full assessment question set.
- If missing: `422` + missing IDs.
- If complete: atomic `DRAFT -> COMPLETED` update setting `completed_at`.
- If already completed: idempotent `200` with existing completion timestamp.

## Error Handling, Testing, and Delivery Priority

- Uniform error envelope everywhere: `code`, `message`, `request_id`, optional `details`.
- Status mapping per spec: `401/403/404/409/422/429/503`.
- Structured logs include request ID and masked PII on auth failures.
- Backend-critical tests:
  - CPF validation
  - rate-limit/lockout (`Retry-After`)
  - IDOR denial
  - draft bootstrap race
  - deterministic shuffle
  - answer restoration
  - submit atomicity/idempotency
  - deny-list `503`
  - ETL empty dataset and masking

## Delivery Priority

1. Functional backend APIs + middleware + indexes + tests.
2. ETL script + ETL tests.
3. Frontend scaffold and endpoint wiring.
4. Deployment and environment docs.
