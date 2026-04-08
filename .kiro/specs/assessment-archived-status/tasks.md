# Implementation Plan: assessment-archived-status

## Overview

Thread the `archived` boolean from MongoDB documents through the API response
model and into the frontend list component. The change is purely additive:
one new field on `CompletedAssessmentSummary`, one mapping line in
`AssessmentService`, and a label + CSS class in `CompletedAssessmentsList`.

## Tasks

- [x] 1. Add `is_archived` field to `CompletedAssessmentSummary`
  - In `backend/app/models/api.py`, add `is_archived: bool` to
    `CompletedAssessmentSummary` after the existing `completed_at` field.
  - No migration needed — all documents already carry `archived`.
  - _Requirements: 1.1, 1.4_

- [x] 2. Map `archived` → `is_archived` in `AssessmentService`
  - In `backend/app/services/assessment_service.py`, inside
    `get_current_assessment`, add `"is_archived": a.get("archived", False)` to
    the dict comprehension that builds the `assessments` list.
  - The repository already sorts by `completed_at DESC`, so no ordering change
    is needed.
  - _Requirements: 1.2, 1.3, 2.1, 2.2, 2.3_

- [x] 3. Install Hypothesis and write backend property-based tests
  - [x] 3.1 Add `hypothesis` to dev dependencies
    - In `backend/pyproject.toml`, add `hypothesis = ">=6.0.0,<7.0.0"` under
      `[tool.poetry.group.dev.dependencies]`.
    - Run `cd backend && poetry add --group dev hypothesis` to update
      `poetry.lock`.
  - [x] 3.2 Write property test for Property 1 (archived mapping)
    - In `backend/tests/test_assessment_service.py`, add a
      `@given(lists(booleans(), min_size=1))` test that builds stub documents
      with mixed `archived` values, calls
      `service.get_current_assessment(student_id=...)`, and asserts every
      summary's `is_archived` equals the corresponding document's `archived`.
    - Tag: `# Feature: assessment-archived-status, Property 1: archived field is faithfully mapped`
    - _Requirements: 1.2, 1.3, 2.2_
  - [ ]* 3.3 Write property test for Property 2 (descending sort)
    - In `backend/tests/test_assessment_service.py`, add a
      `@given(lists(datetimes(...), min_size=2))` test that builds stub
      documents with random `completed_at` values, calls
      `get_current_assessment`, and asserts each entry's `completed_at` is ≥
      the next entry's `completed_at`.
    - Tag: `# Feature: assessment-archived-status, Property 2: assessments list is sorted descending by completed_at`
    - _Requirements: 2.3_

- [x] 4. Checkpoint — ensure backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Update `CompletedAssessmentsList` in `IntroScreen.jsx`
  - In `frontend/src/components/screens/IntroScreen.jsx`, update the
    `CompletedAssessmentsList` function to:
    - Read `assessment.is_archived` for each item.
    - Add `completed-assessment-item--archived` to the `<li>` className when
      `is_archived` is true.
    - Render a `<span>` with class `completed-assessment-item__status` (plus
      `completed-assessment-item__status--archived` when archived) containing
      "Arquivada" or "Válida".
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 6. Add CSS rules for archived status styles
  - In `frontend/src/styles.css`, append three new rule blocks to the
    "Completed assessments list" section:
    - `.completed-assessment-item--archived` — `opacity: 0.55`
    - `.completed-assessment-item__status` — pill badge styles (font-size,
      padding, border-radius, border, background, color)
    - `.completed-assessment-item__status--archived` — muted variant overriding
      border-color, background, and color
  - _Requirements: 3.2, 3.3_

- [x] 7. Install `@fast-check/vitest` and write frontend property-based tests
  - [x] 7.1 Add `@fast-check/vitest` to dev dependencies
    - In `frontend/package.json`, add `"@fast-check/vitest"` to
      `devDependencies`.
    - Run `cd frontend && npm install --save-dev @fast-check/vitest` to update
      `package-lock.json`.
  - [ ]* 7.2 Write property test for Property 3 (status label)
    - In `frontend/src/test/IntroScreen.test.jsx`, add a `test.prop` test using
      `fc.array(fc.record({ assessment_id: fc.string(), assessment_type: fc.string(), completed_at: fc.string(), is_archived: fc.boolean() }), { minLength: 1 })`.
    - For each rendered item, assert the `.completed-assessment-item__status`
      span contains "Válida" when `is_archived` is false and "Arquivada" when
      true.
    - Tag: `// Feature: assessment-archived-status, Property 3: status label matches is_archived value`
    - _Requirements: 3.1, 3.2_
  - [ ]* 7.3 Write property test for Property 4 (archived CSS class)
    - In `frontend/src/test/IntroScreen.test.jsx`, add a `test.prop` test with
      the same generator.
    - For each rendered item, assert the `<li>` has class
      `completed-assessment-item--archived` if and only if `is_archived` is
      true.
    - Tag: `// Feature: assessment-archived-status, Property 4: archived CSS class applied iff is_archived is true`
    - _Requirements: 3.3_

- [x] 8. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Each task references specific requirements for traceability.
- `hypothesis` is not yet in `pyproject.toml`; task 3.1 adds it.
- `@fast-check/vitest` is not yet in `package.json`; task 7.1 adds it.
- The `_AssessmentRepositoryStub` in `test_assessment_service.py` already
  returns documents with `archived` set, so no stub changes are needed.
