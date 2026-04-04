# Project Structure

```
backend/
  app/
    api/
      routes/       # FastAPI routers — one file per resource (auth.py, assessments.py, health.py)
      deps.py       # FastAPI dependencies (service injection, auth context)
    core/
      config.py     # Settings via pydantic-settings (loaded from .env)
      errors.py     # AppError dataclass — the single error type raised by services
      security.py   # JWT encode/decode helpers
      utils.py      # CPF validation/normalization
    db/
      mongo.py      # Motor client setup
      collections.py # Collection accessors
      indexes.py    # Index definitions, called at startup
    models/
      domain.py     # Pydantic domain models (Student, Question, Assessment, etc.)
      api.py        # Pydantic request/response models
    repositories/   # MongoDB access only — no business logic
    services/       # Business logic only — no direct DB access
    main.py         # App factory, lifespan wiring, middleware, exception handlers
  tests/            # pytest tests; use stub repositories, not real DB
  scripts/          # One-off data scripts (seed_questions.py, seed_students.py)

frontend/
  src/
    components/
      screens/      # One component per app stage (AuthScreen, IntroScreen, QuestionsScreen, CompletionScreen)
      ui.jsx        # Shared UI primitives
    hooks/
      useAssessmentFlow.js  # Central state machine for the entire app flow
    utils/
      http.js       # fetch helpers (readApiError, wait)
      formatters.js # Data formatting utilities
    content/
      stageContent.js # Static copy/content strings (pt-BR)
    config.js       # STAGES enum, API_BASE, SESSION_KEY constants
    App.jsx         # Root component — renders the active stage screen
    styles.css      # All styles (no CSS modules or styled-components)

docs/             # Architecture docs, design notes, task lists
assets/           # Design assets, exam source files
infra/            # Render deployment config
scripts/          # Root-level ETL scripts (extract.py)
```

## Architecture Patterns

**Backend layering** (strict — do not cross layers):
- Routers → call services via `request.state` (injected in lifespan)
- Services → all business logic; raise `AppError` for domain errors
- Repositories → raw MongoDB operations only, return plain dicts
- Services never import repositories directly; they receive them via constructor injection

**Error handling:**
- All expected errors use `AppError(status_code, code, message, details)`
- `code` is SCREAMING_SNAKE_CASE (e.g. `ASSESSMENT_NOT_FOUND`)
- Global exception handlers in `main.py` convert `AppError` → JSON response with shape `{code, message, request_id, details}`

**Frontend state:**
- All app state lives in `useAssessmentFlow` hook
- Screen components are stateless — they receive props and call callbacks
- App stage is driven by the `STAGES` enum in `config.js`
- Session (token + assessmentId) is persisted to `localStorage` under `SESSION_KEY`

**Testing:**
- Backend tests use hand-written stub repositories (no mocking libraries, no real DB)
- Tests are async (`@pytest.mark.asyncio`) and live in `backend/tests/`
