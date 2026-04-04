# Implementation Plan: assessment-level-selection

## Overview

Extend the assessment flow so students can choose a difficulty level before starting. The remaining work covers: ULID-based student identity, collection injection in repositories, DB-level question filtering, the new archive-based one-active-assessment invariant, updated service algorithms, index changes, and test coverage. Changes follow the project's strict layering: domain models → seed/auth → repository → service → API → frontend → tests → Figma.

## Tasks

- [x] 1. Extend domain model and API models with level support
  - `AssessmentLevel` enum added to `domain.py`
  - `level` field added to `Assessment` model
  - `CreateAssessmentRequest`, `CreateAssessmentResponse`, `CompletedAssessmentSummary`, `AssessmentSummaryResponse` updated in `api.py`
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Add `archived` field to Assessment domain model and `student_id` to Student domain model
  - Add `archived: bool = False` field to the `Assessment` Pydantic model in `backend/app/models/domain.py`
  - Add `student_id: str` field to the `Student` Pydantic model in `backend/app/models/domain.py`
  - _Requirements: 1.2, 1.4, 2.1_

- [ ] 3. Add `python-ulid` dependency and update seed script
  - Add `python-ulid` to `backend/pyproject.toml` via `poetry add python-ulid`
  - Update `backend/scripts/seed_students.py` to generate a ULID (`from ulid import ULID; str(ULID())`) for each student and include `student_id` in the `$set` document on upsert; use `$setOnInsert` so existing documents without `student_id` receive it on the next upsert run
  - _Requirements: 2.1_

- [ ] 4. Update AuthRepository and AuthService to use `student_id` ULID
  - Update `AuthRepository.__init__` to accept a `collection` parameter (same injection pattern as AssessmentRepository below) — or at minimum ensure `find_student_by_cpf_and_birth_date` returns the `student_id` field
  - Update `AuthService.authenticate_and_issue_token` to pass `student_id=str(student["student_id"])` (the ULID) to `create_access_token` instead of `str(student["_id"])`
  - Update `AuthService.validate_access` ownership check: compare `str(record["student_id"])` against `payload["sub"]` (both are now ULIDs)
  - _Requirements: 2.2, 2.3_

- [ ] 5. Refactor AssessmentRepository to use collection injection
  - Change `AssessmentRepository.__init__` to accept `collection` and `questions_collection` parameters and store them as `self.collection` and `self.questions_collection`
  - Replace all `assessments_collection(self.db)` calls with `self.collection` and all `questions_collection(self.db)` calls with `self.questions_collection` throughout the file
  - Update `backend/app/main.py` lifespan to wire: `AssessmentRepository(collection=assessments_collection(db), questions_collection=questions_collection(db))`
  - _Requirements: 1.5_

- [ ] 6. Add `list_questions_for_level` and new query methods to AssessmentRepository
  - Add `list_questions_for_level(self, *, level: str) -> list[dict]` that queries `self.questions_collection.find({"category": level}, {"_id": 1, "number": 1, "category": 1})`
  - Add `find_active_assessment_by_student(self, *, student_id: str) -> dict | None` that queries `self.collection.find_one({"student_id": student_id, "archived": {"$ne": True}})`
  - Add `find_all_completed_assessments_by_student(self, *, student_id: str) -> list[dict]` that queries `self.collection.find({"student_id": student_id, "status": "COMPLETED"}, sort=[("completed_at", -1)])` — includes archived
  - Add `archive_assessment(self, *, assessment_id: ObjectId) -> None` that sets `archived=True` on the document
  - Update `create_assessment` signature: change `student_id` parameter type from `ObjectId` to `str` (ULID) and add `archived: False` to the inserted document
  - _Requirements: 1.2, 1.5, 4.1, 4.3, 5.1, 6.3_

- [ ] 7. Remove `LEVEL_CATEGORY_MAP` and update `build_assigned_question_ids`
  - Remove `LEVEL_CATEGORY_MAP` constant from `backend/app/services/question_selection.py`
  - Remove the in-Python category filtering (`filtered_docs = [q for q in question_docs if ...]`) from `build_assigned_question_ids`
  - `build_assigned_question_ids` now receives a pre-filtered pool from `list_questions_for_level` and passes it directly to `select_questions_by_difficulty`
  - Keep the `level` parameter signature for forward compatibility but it no longer drives filtering
  - _Requirements: 3.1, 3.2_

  - [ ]* 7.1 Write property test for question category containment (Property 1)
    - **Property 1: All returned IDs belong to the exact level category**
    - **Validates: Requirements 3.2**
    - Use `hypothesis` to generate arbitrary question pools (all pre-filtered to a single category) and assert every returned ID has `category == level`

  - [ ]* 7.2 Write property test for question count bound (Property 2)
    - **Property 2: Result count ≤ assessment_question_count**
    - **Validates: Requirements 3.3**
    - Use `hypothesis`; assert `len(result) <= settings.assessment_question_count` for any pool

- [ ] 8. Rewrite AssessmentService with new 4-step algorithm
  - Rewrite `create_assessment` to implement the design algorithm:
    1. `find_all_completed_assessments_by_student` → if level in history → raise `LEVEL_ALREADY_COMPLETED` (409)
    2. `find_active_assessment_by_student` → if same level + DRAFT → return idempotently
    3. If active exists at different level → `archive_assessment`, then fall through to step 4
    4. `list_questions_for_level(level)` → `build_assigned_question_ids` → `create_assessment` in repo
  - Change `student_id` handling: remove `_ensure_object_id` conversion — `student_id` is now a ULID string passed directly to the repository
  - Handle `DuplicateKeyError` by re-fetching via `find_active_assessment_by_student` and returning the existing draft
  - Rewrite `get_current_assessment` to use two queries: `find_active_assessment_by_student` (non-archived) + `find_all_completed_assessments_by_student` (full history including archived); top-level fields reflect the active assessment; `assessments` array is the full completed history
  - _Requirements: 1.3, 1.4, 3.2, 3.4, 4.1, 4.2, 4.3, 4.5, 5.1, 5.2, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 8.1 Write unit tests for `create_assessment` new algorithm in `backend/tests/test_assessment_service.py`
    - Extend `_AssessmentRepositoryStub` with `find_active_assessment_by_student`, `find_all_completed_assessments_by_student`, `archive_assessment`, and `list_questions_for_level`; use ULID strings as `student_id` in all fixtures
    - Test: no active + no history → creates new DRAFT
    - Test: active DRAFT at same level → returns existing DRAFT (idempotent, no new doc)
    - Test: active DRAFT at different level → archives it, creates new DRAFT at new level
    - Test: active COMPLETED at different level → archives it, creates new DRAFT at new level
    - Test: level in completed history (archived or not) → raises `LEVEL_ALREADY_COMPLETED`, no doc created/modified
    - Test: empty question pool → raises `NO_QUESTIONS_FOR_LEVEL`
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 3.4_

  - [ ]* 8.2 Write unit tests for `get_current_assessment` new algorithm
    - Test: active DRAFT + completed history → top-level reflects DRAFT, `assessments` = full history
    - Test: no active + completed history (including archived) → `status: "NONE"`, `assessments` = full history
    - Test: archived completed assessments appear in `assessments`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 8.3 Write property test for create_assessment idempotency (Property 3)
    - **Property 3: Two calls with same student+level return the same assessment_id**
    - **Validates: Requirements 4.2**
    - Use `hypothesis`; assert second call returns same `assessment_id` and exactly one non-archived assessment exists

  - [ ]* 8.4 Write property test for completed level permanently locked (Property 4)
    - **Property 4: Completed level is permanently locked (including archived)**
    - **Validates: Requirements 5.1**
    - Use `hypothesis`; for any student with a COMPLETED assessment (archived or not) at a level, every `create_assessment` call for that level raises `LEVEL_ALREADY_COMPLETED`

  - [ ]* 8.5 Write property test for one-active-assessment invariant (Property 5)
    - **Property 5: After create_assessment, exactly one non-archived assessment exists per student**
    - **Validates: Requirements 4.5**
    - Use `hypothesis`; after any sequence of `create_assessment` calls, count of non-archived assessments for the student is exactly 1

  - [ ]* 8.6 Write property test for completed assessments completeness and ordering (Property 6)
    - **Property 6: `assessments` array contains all COMPLETED entries sorted by completed_at descending**
    - **Validates: Requirements 6.3, 6.4**
    - Use `hypothesis`; assert `assessments` contains exactly all COMPLETED docs (archived or not) sorted descending

- [ ] 9. Update MongoDB indexes
  - In `backend/app/db/indexes.py`, replace the existing `uq_assessment_student_level_draft` index with a partial unique index on `{ student_id: 1 }` with `partialFilterExpression: { archived: { $ne: True } }` — enforces at most one non-archived assessment per student
  - Add a compound index on `{ student_id: 1, status: 1, completed_at: -1 }` for completed-history lookups
  - Add a unique index on `{ student_id: 1 }` on the students collection for O(1) ULID lookups
  - _Requirements: 2.4, 7.1, 7.2_

- [ ] 10. Wire AssessmentRepository collection injection in `main.py`
  - Update the lifespan in `backend/app/main.py` to construct `AssessmentRepository(collection=assessments_collection(db), questions_collection=questions_collection(db))`
  - Import `assessments_collection` and `questions_collection` from `app.db.collections` in `main.py`
  - _Requirements: 1.5_

- [ ] 11. Backend checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Update API route for `POST /assessments` and `GET /assessments/current`
  - `POST /assessments` accepts `CreateAssessmentRequest` body and passes `level` to the service — already done
  - `GET /assessments/current` returns updated `AssessmentSummaryResponse` with `assessments` array — already done
  - _Requirements: 4.4, 6.1_

  - [ ]* 12.1 Write HTTP API integration tests in `backend/tests/test_http_api.py`
    - Test `POST /assessments` with each valid level returns `{ assessment_id, status, level }`
    - Test `POST /assessments` with invalid level returns HTTP 422
    - Test `POST /assessments` for a completed level returns HTTP 409 `LEVEL_ALREADY_COMPLETED`
    - Test `POST /assessments` with a different level archives the old assessment and returns a new DRAFT
    - Test `GET /assessments/current` top-level fields reflect the non-archived assessment; `assessments` includes all completed history (archived or not)
    - _Requirements: 4.1, 4.3, 4.4, 5.1, 6.2, 6.3_

- [x] 13. Update `useAssessmentFlow` hook with level state
  - `selectedLevel`, `completedAssessments`, `assessmentLevel` state added — already done
  - `loadCurrentAssessment` populates `completedAssessments` from `data.assessments` — already done
  - `startAssessment(level)` sends `{ level }` in POST body — already done
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 14. Update IntroScreen with level picker and completed assessments list
  - Level picker with four cards, completed badge, disabled state — already done
  - Completed assessments list — already done
  - `App.jsx` wired up — already done
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2_

  - [ ]* 14.1 Write property test for completed levels non-selectable (Property 7)
    - **Property 7: Completed levels are disabled in the picker**
    - **Validates: Requirements 8.3**
    - Use `hypothesis` with arbitrary `completedAssessments` arrays; assert every completed level's button has `disabled` and shows "Concluído" badge

  - [ ]* 14.2 Write property test for start button disabled invariant (Property 8)
    - **Property 8: Start button is disabled when isBusy or no level selected or selected level is completed**
    - **Validates: Requirements 8.5**
    - Use `hypothesis`; assert button has `disabled` for any combination of those conditions

  - [ ]* 14.3 Write property test for completed assessments list completeness (Property 9)
    - **Property 9: Completed assessments list renders one entry per element**
    - **Validates: Requirements 9.1**
    - Use `hypothesis`; for any non-empty `completedAssessments`, assert the rendered list contains one entry per element with level name and completion date

- [ ] 15. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Update Figma design
  - Update the Figma file at https://www.figma.com/design/zSYPF89omQ51ZuPKPyuBZw/Evaluation-System?node-id=0-1&m=dev to reflect the level picker and completed assessments list screens
  - _Requirements: 11.1_

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Backend tests use hand-written stub repositories — no mocking libraries, no real DB
- All tests are async with `@pytest.mark.asyncio` (`asyncio_mode = "auto"`)
- Property-based tests use the `hypothesis` library
- `python-ulid` must be added as a dependency before tasks 3–8
- The `student_id` ULID migration: existing student documents without `student_id` will receive it on the next seed upsert run; assessment documents created before this change used ObjectId as `student_id` and will be incompatible — a one-time migration or clean re-seed is required in non-production environments
- Tasks 10 and 5 are closely related — collection injection in the repository must be done before wiring in `main.py`
