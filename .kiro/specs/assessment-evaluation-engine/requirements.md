# Requirements Document

## Introduction

The Assessment Evaluation Engine adds weighted scoring, classification, and persisted evaluation snapshots to the Kodie platform. It renames the `level` field to `assessment_type` (and `AssessmentLevel` enum to `AssessmentType`) as a clean, complete rename across all layers. The engine computes a structured `evaluation_result` snapshot atomically on assessment completion, and exposes admin-facing APIs for results, analytics, and ranking.

## Glossary

- **Evaluation_Engine**: The backend service responsible for computing weighted scores, per-level performance, and classification from a completed assessment's answers and question metadata.
- **Assessment_Service**: The existing FastAPI service layer that manages assessment lifecycle (create, answer, submit).
- **Assessment_Repository**: The existing MongoDB repository layer for assessment and question documents.
- **Admin_API**: The set of HTTP endpoints accessible only to authenticated admin users, returning results, analytics, and ranking data.
- **Snapshot**: The `evaluation_result` sub-document persisted atomically inside an assessment document when it transitions from `DRAFT` to `COMPLETED`.
- **Ranking_Service**: The backend service responsible for computing assessment-type and global normalized leaderboards.
- **Analytics_Service**: The backend service responsible for aggregating score distributions, classification distributions, and per-level accuracy metrics.
- **AssessmentType**: The renamed enum (formerly `AssessmentLevel`) with values `iniciante`, `junior`, `pleno`, `senior`, `geral`. The `assessment_type` field on Assessment documents replaces the former `level` field.
- **score_total**: The sum of points earned from correctly answered questions, using per-level weights.
- **score_max**: The maximum achievable score for a given `assessment_type`.
- **score_percent**: `(score_total / score_max) * 100`, rounded to two decimal places.
- **performance_by_level**: A map from each canonical level (`iniciante`, `junior`, `pleno`, `senior`) to `{ correct, total, accuracy }`.
- **classification_kind**: Either `"level_fit"` (single-level assessments) or `"consistency_level"` (`geral` assessments).
- **classification_value**: The outcome string — one of `below_expected | at_level | above_expected` for `level_fit`, or one of `iniciante | junior | pleno | senior` for `consistency_level`.
- **Canonical_Level**: One of the four ordered levels: `iniciante`, `junior`, `pleno`, `senior`.
- **DONT_KNOW**: A valid answer option that contributes 0 points, equivalent to an incorrect answer for scoring purposes.

---

## Requirements

### Requirement 1: Question Weights and Score Calculation

**User Story:** As the platform, I want each question to carry a point value based on its difficulty level, so that harder questions contribute more to a student's total score.

#### Acceptance Criteria

1. THE Evaluation_Engine SHALL assign `2` points to each correctly answered question with category `iniciante`.
2. THE Evaluation_Engine SHALL assign `3` points to each correctly answered question with category `junior`.
3. THE Evaluation_Engine SHALL assign `4` points to each correctly answered question with category `pleno`.
4. THE Evaluation_Engine SHALL assign `5` points to each correctly answered question with category `senior`.
5. WHEN a student selects a wrong answer or `DONT_KNOW` for a question, THE Evaluation_Engine SHALL contribute `0` points for that question to `score_total`.
6. THE Evaluation_Engine SHALL compute `score_total` as the sum of points earned from all correctly answered questions in the assessment.

---

### Requirement 2: Score Ceilings by Assessment Type

**User Story:** As the platform, I want each assessment type to have a defined maximum score, so that results can be normalized and compared fairly.

#### Acceptance Criteria

1. THE Evaluation_Engine SHALL set `score_max` to `40` for assessments with `assessment_type = "iniciante"`.
2. THE Evaluation_Engine SHALL set `score_max` to `60` for assessments with `assessment_type = "junior"`.
3. THE Evaluation_Engine SHALL set `score_max` to `80` for assessments with `assessment_type = "pleno"`.
4. THE Evaluation_Engine SHALL set `score_max` to `100` for assessments with `assessment_type = "senior"`.
5. THE Evaluation_Engine SHALL set `score_max` to `70` for assessments with `assessment_type = "geral"`.
6. THE Evaluation_Engine SHALL compute `score_percent` as `(score_total / score_max) * 100`, rounded to two decimal places.

---

### Requirement 3: Per-Level Performance Calculation

**User Story:** As an admin, I want to see how a student performed at each difficulty level, so that I can identify specific strengths and gaps regardless of assessment type.

#### Acceptance Criteria

1. THE Evaluation_Engine SHALL compute `performance_by_level` for all four Canonical_Levels (`iniciante`, `junior`, `pleno`, `senior`) for every completed assessment.
2. THE Evaluation_Engine SHALL set `correct` in each level entry to the count of questions at that level answered with the correct option.
3. THE Evaluation_Engine SHALL set `total` in each level entry to the count of questions at that level assigned to the assessment.
4. THE Evaluation_Engine SHALL set `accuracy` in each level entry to `correct / total` when `total > 0`.
5. WHEN `total = 0` for a Canonical_Level, THE Evaluation_Engine SHALL set `accuracy` to `null` for that level.

---

### Requirement 4: Classification for Single-Level Assessments

**User Story:** As an admin, I want single-level assessments to be classified by how the student performed relative to the level's ceiling, so that I can quickly understand whether the student is below, at, or above the expected standard.

#### Acceptance Criteria

1. WHEN `assessment_type` is one of `iniciante`, `junior`, `pleno`, or `senior`, THE Evaluation_Engine SHALL set `classification_kind` to `"level_fit"`.
2. WHEN `score_percent < 50`, THE Evaluation_Engine SHALL set `classification_value` to `"below_expected"`.
3. WHEN `score_percent >= 50` AND `score_percent <= 70`, THE Evaluation_Engine SHALL set `classification_value` to `"at_level"`.
4. WHEN `score_percent > 70`, THE Evaluation_Engine SHALL set `classification_value` to `"above_expected"`.

---

### Requirement 5: Classification for Geral Assessments

**User Story:** As an admin, I want `geral` assessments to be classified by the highest level at which the student demonstrated consistent performance, so that I can identify the student's effective proficiency level across all domains.

#### Acceptance Criteria

1. WHEN `assessment_type = "geral"`, THE Evaluation_Engine SHALL set `classification_kind` to `"consistency_level"`.
2. WHEN `assessment_type = "geral"`, THE Evaluation_Engine SHALL set `classification_value` to the highest Canonical_Level for which `accuracy >= 0.70` in `performance_by_level`, evaluated in ascending order (`iniciante` → `junior` → `pleno` → `senior`).
3. WHEN no Canonical_Level has `accuracy >= 0.70`, THE Evaluation_Engine SHALL set `classification_value` to `"iniciante"`.

---

### Requirement 6: Assessment Type Field Rename

**User Story:** As the platform, I want the `level` field renamed to `assessment_type` across all layers, so that the codebase uses consistent, self-describing terminology.

#### Acceptance Criteria

1. THE Assessment_Repository SHALL store and retrieve the `assessment_type` field on assessment documents in place of the former `level` field.
2. THE Assessment_Repository SHALL use `assessment_type` in all query filters, projections, and write operations — no `level` field SHALL remain in any repository method signature or MongoDB document.
3. THE Assessment_Service SHALL accept `assessment_type` in all method signatures where `level` was previously used.
4. THE Assessment_Service SHALL return `assessment_type` in all response dicts where `level` was previously returned.
5. THE Admin_API SHALL expose `assessment_type` in all request and response contracts — no `level` field SHALL appear in any API schema.
6. THE domain model SHALL rename the `AssessmentLevel` enum to `AssessmentType` and the `Assessment.level` field to `Assessment.assessment_type`.

---

### Requirement 7: Assessment Type Persistence on Creation

**User Story:** As the platform, I want `assessment_type` to be stored on the assessment document at creation time, so that all downstream evaluation and reporting logic can rely on it without recomputation.

#### Acceptance Criteria

1. THE Assessment_Service SHALL accept `assessment_type` (one of `iniciante`, `junior`, `pleno`, `senior`, `geral`) in the assessment creation request body.
2. THE Assessment_Service SHALL persist `assessment_type` on the assessment document at creation time.
3. IF an invalid `assessment_type` value is provided, THEN THE Assessment_Service SHALL return a `422` response with code `INVALID_ASSESSMENT_TYPE`.
4. THE Assessment_Service SHALL preserve the existing idempotency behavior: returning the existing DRAFT when a student requests the same `assessment_type` that is already in DRAFT state.

---

### Requirement 8: Evaluation Snapshot Persistence on Completion

**User Story:** As the platform, I want the evaluation result to be computed and stored atomically when an assessment is completed, so that result data is always consistent with the answers recorded at submission time.

#### Acceptance Criteria

1. WHEN an assessment transitions from `DRAFT` to `COMPLETED`, THE Assessment_Service SHALL compute the full `evaluation_result` snapshot and write it atomically to the assessment document in the same database operation.
2. THE Snapshot SHALL contain: `assessment_type`, `score_total`, `score_max`, `score_percent`, `performance_by_level`, `classification_kind`, `classification_value`, `duration_seconds`, `correct_count`, `incorrect_count`, `dont_know_count`, `evaluated_at`.
3. THE Evaluation_Engine SHALL compute `duration_seconds` as the integer number of seconds between `started_at` and `completed_at`.
4. THE Evaluation_Engine SHALL compute `correct_count` as the total number of questions answered with the correct option across all levels.
5. THE Evaluation_Engine SHALL compute `incorrect_count` as the total number of questions answered with a wrong option (excluding `DONT_KNOW`).
6. THE Evaluation_Engine SHALL compute `dont_know_count` as the total number of questions answered with `DONT_KNOW`.
7. WHEN `submit_assessment` is called on an assessment that already has `status = "COMPLETED"`, THE Assessment_Service SHALL return the existing result without recomputing or overwriting the snapshot.

---

### Requirement 9: Admin Results API

**User Story:** As an admin, I want to retrieve paginated assessment results with full evaluation data, so that I can review student performance across all completed assessments.

#### Acceptance Criteria

1. THE Admin_API SHALL expose a paginated endpoint that returns completed assessments with the following fields per result: `assessment_id`, `student_id`, `assessment_type`, `score_total`, `score_max`, `score_percent`, `performance_by_level`, `classification_kind`, `classification_value`, `duration_seconds`, `completed_at`.
2. THE Admin_API SHALL support filtering results by `assessment_type`.
3. THE Admin_API SHALL support filtering results by `classification_value`.
4. THE Admin_API SHALL mask or omit personally identifiable student fields in the results list response.
5. THE Admin_API SHALL expose a detail endpoint that returns all fields from the Snapshot plus per-question correctness detail for a single assessment.
6. WHEN a requested assessment does not exist, THE Admin_API SHALL return a `404` response with code `ASSESSMENT_NOT_FOUND`.

---

### Requirement 10: Analytics API

**User Story:** As an admin, I want aggregated analytics over completed assessments, so that I can understand score distributions, classification outcomes, and per-level accuracy trends across the student population.

#### Acceptance Criteria

1. THE Analytics_Service SHALL compute score distribution by raw `score_total` (count of assessments per score value).
2. THE Analytics_Service SHALL compute score distribution by normalized `score_percent` (bucketed into ranges of `10` percentage points).
3. THE Analytics_Service SHALL compute classification distribution (count of assessments per `classification_value`).
4. THE Analytics_Service SHALL compute per-level accuracy analytics (mean `accuracy` per Canonical_Level across all assessments that include that level).
5. THE Admin_API SHALL support filtering all analytics by `assessment_type`.
6. WHERE `assessment_type` filter is not provided, THE Admin_API SHALL return analytics aggregated across all assessment types.

---

### Requirement 11: Assessment-Type Ranking API

**User Story:** As an admin, I want to see a leaderboard of students ranked within the same assessment type, so that I can compare performance among students who took the same exam.

#### Acceptance Criteria

1. THE Ranking_Service SHALL rank completed assessments of the same `assessment_type` by `score_total` descending.
2. WHEN two assessments have equal `score_total`, THE Ranking_Service SHALL apply tie-breakers in order: `duration_seconds` ascending, then `completed_at` ascending.
3. THE Admin_API SHALL expose a paginated assessment-type ranking endpoint that accepts `assessment_type` as a required filter.
4. THE Admin_API SHALL return `rank`, `assessment_id`, `student_id`, `score_total`, `score_max`, `score_percent`, `classification_value`, `duration_seconds`, `completed_at` per entry.

---

### Requirement 12: Global Normalized Ranking API

**User Story:** As an admin, I want a global leaderboard that normalizes scores across all assessment types, so that I can compare students who took different exams on equal footing.

#### Acceptance Criteria

1. THE Ranking_Service SHALL rank all completed assessments by `score_percent` descending (normalized score `score_total / score_max * 100`).
2. WHEN two assessments have equal `score_percent`, THE Ranking_Service SHALL apply tie-breakers in order: `score_total` descending, then `duration_seconds` ascending, then `completed_at` ascending.
3. THE Admin_API SHALL expose a paginated global ranking endpoint that includes assessments of all `assessment_type` values.
4. THE Admin_API SHALL return `rank`, `assessment_id`, `student_id`, `assessment_type`, `score_total`, `score_max`, `score_percent`, `classification_value`, `duration_seconds`, `completed_at` per entry.
