# Kodie Backend

## Current Architecture

- `routers` depend on service instances resolved from the FastAPI lifespan state
- `services` contain business rules only
- `repositories` encapsulate MongoDB access
- question assignment is snapshotted into `assessments.assigned_question_ids`
- answers are embedded in `assessments.answers`

## Install

```bash
poetry install
```

## Run

```bash
poetry run uvicorn app.main:app --reload
```

## Test

```bash
poetry run pytest -q
```

If `pytest` is not installed in the local virtualenv, install dev dependencies first with:

```bash
poetry install --with dev
```

## API Summary

```text
GET    /live
GET    /ready
POST   /auth
POST   /auth/revoke
GET    /assessments/{assessment_id}/questions?quantity={n}
PATCH  /assessments/{assessment_id}/answers
POST   /assessments/{assessment_id}/submit
```

Notes:

- `GET /ready` checks MongoDB and returns dependency status plus elapsed time
- `GET /assessments/{assessment_id}/questions` accepts optional `quantity`
- the question set is frozen per assessment through `assigned_question_ids`
- answers are saved inside the `assessments` document

## Seed Students

Seed the `students` collection used by `/auth` with a CSV containing `cpf,name,birth_date`:

```bash
poetry run python scripts/seed_students.py scripts/students.sample.csv
```

Dry-run validation:

```bash
poetry run python scripts/seed_students.py scripts/students.sample.csv --dry-run
```

## Seed Questions

Seed the `questions` collection from the bundled exam file:

```bash
poetry run python scripts/seed_questions.py
```

Dry-run validation:

```bash
poetry run python scripts/seed_questions.py --dry-run
```
