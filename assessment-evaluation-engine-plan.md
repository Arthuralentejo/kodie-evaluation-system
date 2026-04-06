# Assessment Evaluation Engine Plan

## Summary

This project owns the assessment evaluation rules and the backend contracts consumed by the admin dashboard.

Scope:
- weighted scoring and classification engine
- new `geral` assessment type
- persisted evaluation snapshots on assessment completion
- admin-facing results, analytics, and ranking APIs

## Core Rules

### Question weights

- `iniciante`: `2` points
- `junior`: `3` points
- `pleno`: `4` points
- `senior`: `5` points

### Score calculation

- `score_total = sum(points of correct answers)`
- wrong answers and `DONT_KNOW` contribute `0` points

### Score ceilings by assessment type

- `iniciante`: `40`
- `junior`: `60`
- `pleno`: `80`
- `senior`: `100`
- `geral`: `70`

### Per-level performance structure

The engine must calculate and persist per-level performance for all canonical levels, even when the selected assessment type is not `geral`.

```json
{
  "iniciante": { "correct": 0, "total": 0, "accuracy": null },
  "junior": { "correct": 0, "total": 0, "accuracy": null },
  "pleno": { "correct": 0, "total": 0, "accuracy": null },
  "senior": { "correct": 0, "total": 0, "accuracy": null }
}
```

Rules:
- `correct` = number of correctly answered questions at that level
- `total` = number of assigned questions at that level
- `accuracy = correct / total`
- when `total = 0`, `accuracy = null`

### Classification rules

For `geral`:
- classify by consistency
- final level is the highest level with `accuracy >= 70%`
- `classification_kind = "consistency_level"`
- `classification_value` is one of `iniciante|junior|pleno|senior`

For single-level assessments:
- classification is based on score percentage against that assessment's `score_max`
- `< 50%` => `below_expected`
- `50% - 70%` => `at_level`
- `> 70%` => `above_expected`
- `classification_kind = "level_fit"`
- `classification_value` is one of `below_expected|at_level|above_expected`

## Data Model Changes

### Assessment document

Add:
- `assessment_type`
- `evaluation_result`

`assessment_type` values:
- `iniciante`
- `junior`
- `pleno`
- `senior`
- `geral`

### Evaluation result snapshot

Persist the evaluation snapshot atomically when an assessment transitions from `DRAFT` to `COMPLETED`.

Required fields:
- `assessment_type`
- `score_total`
- `score_max`
- `score_percent`
- `performance_by_level`
- `classification_kind`
- `classification_value`
- `duration_seconds`
- `correct_count`
- `incorrect_count`
- `dont_know_count`
- `evaluated_at`

Recommended extra fields:
- weighted scoring breakdown per question
- per-question correctness detail for admin result inspection

### Public contract defaults

Assessment creation contract:

```json
{
  "assessment_type": "iniciante|junior|pleno|senior|geral"
}
```

Evaluation result contract for `geral`:

```json
{
  "assessment_type": "geral",
  "score_total": 52,
  "score_max": 70,
  "score_percent": 74.29,
  "performance_by_level": {
    "iniciante": { "correct": 5, "total": 5, "accuracy": 1.0 },
    "junior": { "correct": 4, "total": 5, "accuracy": 0.8 },
    "pleno": { "correct": 2, "total": 5, "accuracy": 0.4 },
    "senior": { "correct": 1, "total": 5, "accuracy": 0.2 }
  },
  "classification_kind": "consistency_level",
  "classification_value": "junior"
}
```

Single-level result contract:

```json
{
  "assessment_type": "senior",
  "score_total": 72,
  "score_max": 100,
  "score_percent": 72,
  "performance_by_level": {
    "iniciante": { "correct": 0, "total": 0, "accuracy": null },
    "junior": { "correct": 0, "total": 0, "accuracy": null },
    "pleno": { "correct": 0, "total": 0, "accuracy": null },
    "senior": { "correct": 14, "total": 20, "accuracy": 0.7 }
  },
  "classification_kind": "level_fit",
  "classification_value": "above_expected"
}
```

## API and Interface Changes

### Student assessment creation

Replace the current level-only create contract with `assessment_type`.

Required behavior:
- validate `assessment_type`
- keep single-level creation for `iniciante`, `junior`, `pleno`, and `senior`
- add `geral` creation path that assigns `5` questions from each canonical level
- persist `assessment_type` on the created assessment

### Results APIs

Admin result APIs must return weighted-result fields, not inferred frontend-only values.

Required result payload fields:
- `assessment_type`
- `score_total`
- `score_max`
- `score_percent`
- `performance_by_level`
- `classification_kind`
- `classification_value`
- `duration_seconds`

### Analytics APIs

Analytics must support:
- score distribution by raw score
- score distribution by normalized percent
- classification distribution
- per-level accuracy analytics
- analytics grouped and filtered by `assessment_type`

### Ranking APIs

Provide both ranking modes:
- assessment-type leaderboard
- global normalized leaderboard

Assessment-type leaderboard:
- compare only assessments of the same `assessment_type`
- sort primarily by raw `score_total`

Global leaderboard:
- compare all completed assessments
- sort primarily by normalized score `score_total / score_max`

Tie-breakers:
1. normalized score desc for global ranking, or raw score desc for assessment-type ranking
2. raw `score_total` desc
3. `duration_seconds` asc
4. `completed_at` asc

## Implementation Notes

### `geral` assessment composition

Rules:
- exactly `5` assigned questions from each canonical level
- total question count remains `20`
- question ordering strategy must stay deterministic and testable

### Snapshot persistence

Rules:
- evaluate only on completion
- write snapshot atomically with the `COMPLETED` transition
- preserve idempotent submit behavior
- keep reads compatible with legacy assessments until backfill completes

### Backfill

Provide a script or job that:
- scans completed assessments without `evaluation_result`
- reconstructs weighted scores and classifications from stored answers and question metadata
- writes the missing evaluation snapshots safely
- supports dry-run or logging suitable for rollout verification

## Test Plan

Required backend coverage:
- weighted scoring by question difficulty
- `geral` question composition: `5` per level
- `score_max` per assessment type
- `geral` classification by highest qualifying level at `>= 70%`
- single-level classification behavior at the defined percentage thresholds
- result snapshot persistence on submit
- idempotent submit behavior after evaluation snapshot exists
- analytics aggregation correctness
- assessment-type ranking ordering
- global normalized ranking ordering
- legacy backfill correctness

## Assumptions

- canonical level keys remain `iniciante`, `junior`, `pleno`, `senior`
- `geral` is the only mixed-level assessment type in v1
- existing dashboard UI tickets should not define or reimplement evaluation rules
- evaluation APIs stay owned by this project even when they exist primarily to serve the dashboard
