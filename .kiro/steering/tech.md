# Tech Stack

## Backend

- Python 3.12+, FastAPI, Motor (async MongoDB driver), PyMongo
- Pydantic v2 + pydantic-settings for models and config
- PyJWT (HS256) for auth tokens
- Poetry for dependency management
- pytest + pytest-asyncio for tests (`asyncio_mode = "auto"`)

## Frontend

- React 19, Vite 7
- No UI framework — plain CSS (`styles.css`)
- Native `fetch` for HTTP (no axios or react-query)
- npm for package management

## Infrastructure

- MongoDB Atlas (database)
- Render (hosting)
- Config via `.env` files; backend uses `pydantic-settings` to load them

## Common Commands

```bash
# Install all dependencies
make install

# Run backend dev server (port 8000)
make dev-backend

# Run frontend dev server
make dev-frontend

# Run both concurrently
make dev

# Run backend tests
make test-backend
# or: cd backend && poetry run pytest -q

# Build frontend assets
make build-frontend

# Seed questions
cd backend && poetry run python scripts/seed_questions.py

# Seed students from CSV
cd backend && poetry run python scripts/seed_students.py scripts/students.sample.csv
```
