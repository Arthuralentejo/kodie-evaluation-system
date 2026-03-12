# Kodie Backend

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

## Seed Students

Seed the `students` collection used by `/auth` with a CSV containing `cpf,name,birth_date`:

```bash
poetry run python scripts/seed_students.py scripts/students.sample.csv
```

Dry-run validation:

```bash
poetry run python scripts/seed_students.py scripts/students.sample.csv --dry-run
```
