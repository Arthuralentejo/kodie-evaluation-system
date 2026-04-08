# Design Document — assessment-archived-status

## Overview

This feature threads the `archived` boolean that already exists on every MongoDB
assessment document through the API response and into the frontend list
component. The change is purely additive: one new field on an existing response
model, one mapping line in the service, a sort guarantee that the repository
already provides, and a label + CSS class in the React component.

No schema migration is needed — all documents already carry `archived`.

---

## Architecture

The change touches three layers in sequence:

```
MongoDB document
  └─ AssessmentRepository.find_all_completed_assessments_by_student
       (already sorts by completed_at DESC, already returns archived field)
  └─ AssessmentService.get_current_assessment
       maps archived → is_archived in each CompletedAssessmentSummary dict
  └─ CompletedAssessmentSummary (api.py)
       new is_archived: bool field
  └─ GET /assessments/current  →  AssessmentSummaryResponse.assessments[]
  └─ useAssessmentFlow.loadCurrentAssessment
       stores completedAssessments (already passes through all fields)
  └─ CompletedAssessmentsList (IntroScreen.jsx)
       reads is_archived, renders label + CSS class
```

No new endpoints, no new collections, no new services.

---

## Components and Interfaces

### Backend — `CompletedAssessmentSummary` (api.py)

Add one field:

```python
class CompletedAssessmentSummary(BaseModel):
    assessment_id: str
    assessment_type: str
    completed_at: str
    is_archived: bool          # NEW
```

### Backend — `AssessmentService.get_current_assessment` (assessment_service.py)

The list comprehension that builds `assessments` gains one key:

```python
assessments = [
    {
        "assessment_id": str(a["_id"]),
        "assessment_type": a.get("assessment_type", "iniciante"),
        "completed_at": a["completed_at"].isoformat(),
        "is_archived": a.get("archived", False),   # NEW
    }
    for a in completed_history
]
```

`completed_history` is already fetched via
`find_all_completed_assessments_by_student`, which already applies
`sort=[("completed_at", -1)]`, satisfying the descending-order requirement
without any additional change.

### Frontend — `CompletedAssessmentsList` (IntroScreen.jsx)

Each list item gains a status label and a conditional CSS class:

```jsx
function CompletedAssessmentsList({ completedAssessments }) {
  if (!completedAssessments || completedAssessments.length === 0) return null;

  return (
    <div className="completed-assessments">
      <h3>Avaliações concluídas</h3>
      <ul>
        {completedAssessments.map((assessment) => {
          const archived = assessment.is_archived;
          return (
            <li
              key={assessment.assessment_id}
              className={
                'completed-assessment-item' +
                (archived ? ' completed-assessment-item--archived' : '')
              }
            >
              <span className="completed-assessment-item__level">
                {LEVEL_LABELS[assessment.assessment_type] || assessment.assessment_type}
              </span>
              <span
                className={
                  'completed-assessment-item__status' +
                  (archived ? ' completed-assessment-item__status--archived' : '')
                }
              >
                {archived ? 'Arquivada' : 'Válida'}
              </span>
              <span className="completed-assessment-item__date">
                {formatDatePtBR(assessment.completed_at)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

### Frontend — `styles.css`

Two new rule blocks appended to the "Completed assessments list" section:

```css
.completed-assessment-item--archived {
  opacity: 0.55;
}

.completed-assessment-item__status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #b6d9c6;
  background: #d9f0e1;
  color: #3f6f59;
}

.completed-assessment-item__status--archived {
  border-color: var(--color-border);
  background: rgba(255, 255, 255, 0.18);
  color: var(--color-muted);
}
```

---

## Data Models

### MongoDB document (unchanged)

```
{
  _id: ObjectId,
  student_id: str,
  status: "DRAFT" | "COMPLETED",
  archived: bool,          // always present
  assessment_type: str,
  completed_at: datetime | null,
  ...
}
```

### API response — `CompletedAssessmentSummary`

```json
{
  "assessment_id": "abc123",
  "assessment_type": "junior",
  "completed_at": "2025-06-01T14:30:00+00:00",
  "is_archived": true
}
```

`is_archived` is a plain JSON boolean, never null.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all
valid executions of a system — essentially, a formal statement about what the
system should do. Properties serve as the bridge between human-readable
specifications and machine-verifiable correctness guarantees.*

### Property 1: archived field is faithfully mapped

*For any* list of completed assessment documents returned by the repository,
every `CompletedAssessmentSummary` built by `AssessmentService` SHALL have
`is_archived` equal to the `archived` field of the corresponding document.

**Validates: Requirements 1.2, 1.3, 2.2**

### Property 2: assessments list is sorted descending by completed_at

*For any* student with two or more completed assessments, the `assessments`
list returned by `AssessmentService.get_current_assessment` SHALL be ordered
so that each entry's `completed_at` is greater than or equal to the next
entry's `completed_at`.

**Validates: Requirements 2.3**

### Property 3: status label matches is_archived value

*For any* assessment object passed to `CompletedAssessmentsList`, the rendered
label SHALL be "Válida" when `is_archived` is `false` and "Arquivada" when
`is_archived` is `true`.

**Validates: Requirements 3.1, 3.2**

### Property 4: archived CSS class applied iff is_archived is true

*For any* assessment object, the rendered list item SHALL carry the class
`completed-assessment-item--archived` if and only if `is_archived` is `true`.

**Validates: Requirements 3.3**

---

## Error Handling

No new error paths are introduced. The `archived` field is guaranteed to be
present on all documents (the repository already filters and sets it). If a
document were somehow missing the field, `a.get("archived", False)` defaults
to `False`, which is the safe fallback (treat unknown as active rather than
silently hiding it).

On the frontend, if `is_archived` is absent from an API response object (e.g.
an older cached response), `assessment.is_archived` evaluates to `undefined`,
which is falsy — the item renders as "Válida" and without the archived class,
which is the safe default.

---

## Testing Strategy

### Backend unit tests (`backend/tests/test_assessment_service.py`)

Use the existing stub-repository pattern. No real DB, no mocking libraries.

- **Property 1** (archived mapping): generate a list of stub documents with
  mixed `archived` values; assert every summary's `is_archived` matches.
  Run with hypothesis (`@given`) over lists of booleans — minimum 100 iterations.
- **Property 2** (ordering): generate stub documents with random `completed_at`
  datetimes; assert the returned list is sorted descending.
  Run with hypothesis over lists of datetimes — minimum 100 iterations.
- **Example** (1.1 / 1.4): instantiate `CompletedAssessmentSummary` with both
  `is_archived=True` and `is_archived=False`; assert Pydantic serializes the
  field as a JSON boolean.

Property-based testing library: **Hypothesis** (already available in the Python
ecosystem; add `hypothesis` to dev dependencies in `pyproject.toml`).

Tag format for each property test:
`# Feature: assessment-archived-status, Property {N}: {property_text}`

### Frontend unit tests (`frontend/src/test/IntroScreen.test.jsx`)

Use the existing Vitest + React Testing Library setup.

- **Property 3** (label): for a list of assessments with mixed `is_archived`
  values, assert each item shows "Válida" or "Arquivada" correctly.
  Use `@fast-check/vitest` for property-based generation — minimum 100 runs.
- **Property 4** (CSS class): same generated list; assert
  `completed-assessment-item--archived` is present iff `is_archived` is true.
- **Edge case** (3.4): render with `completedAssessments={[]}` and with
  `completedAssessments={undefined}`; assert nothing is rendered.

Property-based testing library: **fast-check** (add `@fast-check/vitest` to
dev dependencies in `package.json`).

Tag format:
`// Feature: assessment-archived-status, Property {N}: {property_text}`
