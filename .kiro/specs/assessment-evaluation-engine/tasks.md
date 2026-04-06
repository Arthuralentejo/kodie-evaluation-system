# Implementation Plan: Assessment Evaluation Engine

## Overview

Implement weighted scoring, classification, persisted evaluation snapshots, and admin-facing results/analytics/ranking APIs. Tasks are grouped by Linear issue. The design uses Python (FastAPI/Motor stack) — all implementation follows the existing layered architecture.

## Tasks

- [x] 1. Domain models and `AssessmentType` rename (ART-17, ART-5)
  - [x] 1.1 Rename `AssessmentLevel` → `AssessmentType` and `Assessment.level` → `Assessment.assessment_type` in `domain.py`
    - Rename the `AssessmentLevel` enum to `AssessmentType` (same values: `iniciante`, `junior`, `pleno`, `senior`, `geral`)
    - Rename `Assessment.level` field to `Assessment.assessment_type`
    - Add `LevelPerformance`, `EvaluationResult`, `QuestionResult` Pydantic models
    - Add `evaluation_result: EvaluationResult | None = None` field to `Assessment`
    - _Requirements: 6.6, 7.1, 8.2_
  - [x] 1.2 Update API models in `api.py` to use `assessment_type` throughout
    - Rename `CreateAssessmentRequest.level` → `assessment_type` (type: `AssessmentType`)
    - Rename `CreateAssessmentResponse.level` → `assessment_type`
    - Rename `CompletedAssessmentSummary.level` → `assessment_type`
    - Rename `AssessmentSummaryResponse.level` → `assessment_type`
    - Replace `AssessmentLevel` import with `AssessmentType`
    - Add `LevelPerformanceResponse`, `EvaluationResultResponse`, `AdminResultSummary`, `AdminResultDetail`, `QuestionResultResponse`, `RankingEntry`, `RankingPage`, `ScoreDistributionBucket`, `LevelAccuracyStat`, `AnalyticsResult`
    - _Requirements: 6.5, 7.1, 9.1, 9.5, 10.1, 11.4, 12.4_

- [x] 2. Update `AssessmentRepository` for `assessment_type` (ART-17, ART-5)
  - [x] 2.1 Update `AssessmentRepository.create_assessment` to use `assessment_type`
    - Replace `level: str` parameter with `assessment_type: str`
    - Write `assessment_type` field to the document (no `level` field)
    - _Requirements: 6.1, 6.2, 7.2_
  - [x] 2.2 Update all repository methods that filter or project on `"level"` to use `"assessment_type"`
    - Update `find_draft_assessment_by_student` and any other query filters referencing `"level"`
    - Ensure no `"level"` key remains in any MongoDB query, projection, or write operation
    - _Requirements: 6.1, 6.2_

- [x] 3. Update `AssessmentService` for `assessment_type` (ART-17, ART-5)
  - [x] 3.1 Update `AssessmentService.create_assessment` to accept and validate `assessment_type`
    - Replace `level` parameter with `assessment_type`; validate against `AssessmentType` enum, raise `AppError(422, "INVALID_ASSESSMENT_TYPE")` on invalid value
    - Route `geral` to `build_geral_question_ids`; route single-level types to `build_assigned_question_ids`
    - Preserve idempotency: return existing DRAFT when same `assessment_type` already in DRAFT
    - Pass `assessment_type` to `repository.create_assessment`
    - _Requirements: 6.3, 7.1, 7.2, 7.3, 7.4_
  - [x] 3.2 Update `AssessmentService.get_current_assessment` to return `assessment_type`
    - Replace all `a.get("level", ...)` lookups with `a.get("assessment_type", ...)`
    - Return `assessment_type` key in all response dicts (remove `level` key)
    - _Requirements: 6.4_
  - [x] 3.3 Update `assessments.py` router to use `assessment_type`
    - Pass `assessment_type` from `CreateAssessmentRequest` to service
    - Return `CreateAssessmentResponse` with `assessment_type`
    - _Requirements: 6.5, 7.1, 7.3_
  - [ ]* 3.4 Write property test for `assessment_type` round-trip persistence (Property 8)
    - **Property 8: assessment_type round-trip persistence**
    - **Validates: Requirements 7.2**
    - Extend `tests/test_assessment_service.py`

- [x] 4. Update `build_geral_question_ids` to enforce exactly 5 per level (ART-17)
  - [x] 4.1 Rewrite `build_geral_question_ids` in `question_selection.py`
    - Replace dynamic `n // 4` split with a fixed `PER_LEVEL = 5` per canonical level (20 total)
    - Raise `AppError(409, "NO_QUESTIONS_FOR_LEVEL")` when fewer than 5 questions exist for any canonical level
    - _Requirements: 6.1, 6.2, 6.3_
  - [ ]* 4.2 Write property test for geral question composition (Property 6)
    - **Property 6: Geral question composition — exactly 5 per level**
    - **Validates: Requirements 6.1**
    - Extend `tests/test_question_selection.py` using `@given` with Hypothesis
  - [ ]* 4.3 Write property test for geral question selection determinism (Property 7)
    - **Property 7: Geral question selection is deterministic**
    - **Validates: Requirements 6.2**
    - Extend `tests/test_question_selection.py`

- [x] 5. Implement `EvaluationEngine` service (ART-5)
  - [x] 5.1 Create `backend/app/services/evaluation_engine.py` with `EvaluationEngine` class
    - Implement `WEIGHTS`, `SCORE_MAX`, `CANONICAL_LEVELS`, `ACCURACY_THRESHOLD` constants
    - Implement `_compute_score` returning `(score_total, correct_count, incorrect_count, dont_know_count)`
    - Implement `_compute_performance_by_level` for all four canonical levels; set `accuracy=null` when `total=0`
    - Implement `_classify` for both `level_fit` (single-level) and `consistency_level` (geral) paths
    - Implement `evaluate` orchestrating all sub-methods and returning an `EvaluationResult`
    - _Requirements: 1.1–1.6, 2.1–2.6, 3.1–3.5, 4.1–4.4, 5.1–5.3, 8.2–8.6_
  - [ ]* 5.2 Write property tests for weighted score total (Property 1)
    - **Property 1: Weighted score total**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    - Create `tests/test_evaluation_engine.py`
  - [ ]* 5.3 Write property test for `score_percent` formula (Property 2)
    - **Property 2: score_percent formula**
    - **Validates: Requirements 2.6**
  - [ ]* 5.4 Write property test for `performance_by_level` completeness and accuracy (Property 3)
    - **Property 3: performance_by_level completeness and accuracy**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
  - [ ]* 5.5 Write property test for single-level classification thresholds (Property 4)
    - **Property 4: Single-level classification thresholds**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
  - [ ]* 5.6 Write property test for geral classification by highest qualifying level (Property 5)
    - **Property 5: Geral classification by highest qualifying level**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 6. Wire `EvaluationEngine` into submit path and extend repository (ART-5)
  - [x] 6.1 Extend `AssessmentRepository.complete_assessment` to accept and write `evaluation_result`
    - Add `evaluation_result: dict | None = None` parameter
    - Include `evaluation_result` in the `$set` payload when provided (atomic write)
    - _Requirements: 8.1_
  - [x] 6.2 Inject `EvaluationEngine` into `AssessmentService` and update `submit_assessment`
    - Add `evaluation_engine: EvaluationEngine` to `AssessmentService.__init__`
    - In `submit_assessment`: fetch question docs, call `evaluation_engine.evaluate`, pass snapshot to `repository.complete_assessment`
    - Preserve idempotent return when assessment is already `COMPLETED`
    - _Requirements: 8.1, 8.7_
  - [x] 6.3 Wire `EvaluationEngine` in `main.py` lifespan
    - Instantiate `EvaluationEngine` and pass it to `AssessmentService`
    - _Requirements: 8.1_
  - [ ]* 6.4 Write property test for submit producing a complete snapshot (Property 9)
    - **Property 9: Submit produces a complete snapshot**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**
    - Extend `tests/test_assessment_service.py`
  - [ ]* 6.5 Write property test for submit idempotence (Property 10)
    - **Property 10: Submit idempotence**
    - **Validates: Requirements 8.7**
    - Extend `tests/test_assessment_service.py`

- [x] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Add MongoDB indexes for evaluation fields (ART-5)
  - [x] 8.1 Add compound indexes to `backend/app/db/indexes.py`
    - Index on `{ assessment_type: 1, status: 1 }` for results filtering
    - Index on `{ "evaluation_result.classification_value": 1, status: 1 }` for classification filter
    - Index on `{ "evaluation_result.score_total": -1, status: 1 }` for ranking by type
    - Index on `{ "evaluation_result.score_percent": -1, status: 1 }` for global ranking
    - _Requirements: 9.2, 9.3, 11.1, 12.1_

- [x] 9. Extend `AssessmentRepository` with admin query methods (ART-7, ART-8, ART-9)
  - [x] 9.1 Implement `list_completed_assessments` in `AssessmentRepository`
    - Accept `assessment_type`, `classification_value`, `page`, `page_size` optional params
    - Return `(list[dict], total_count)` tuple; project only fields needed for `AdminResultSummary`
    - _Requirements: 9.1, 9.2, 9.3_
  - [x] 9.2 Implement `aggregate_analytics` in `AssessmentRepository`
    - Build and run MongoDB aggregation pipeline for score distribution (raw + normalized buckets), classification distribution, and per-level accuracy
    - Accept optional `assessment_type` filter
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [x] 9.3 Implement `list_completed_assessments_ranked` in `AssessmentRepository`
    - For by-type ranking: sort by `score_total DESC, duration_seconds ASC, completed_at ASC`
    - For global ranking: sort by `score_percent DESC, score_total DESC, duration_seconds ASC, completed_at ASC`
    - _Requirements: 11.1, 11.2, 12.1, 12.2_

- [x] 10. Implement `RankingService` (ART-9)
  - [x] 10.1 Create `backend/app/services/ranking_service.py`
    - Implement `rank_by_type(assessment_type, page, page_size)` — delegates sort to repository, assigns `rank` field based on page offset
    - Implement `rank_global(page, page_size)` — same pattern with global sort
    - Return `RankingPage` with `entries`, `total`, `page`, `page_size`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 12.1, 12.2, 12.3, 12.4_
  - [ ]* 10.2 Write property test for ranking sort order — by type (Property 11)
    - **Property 11: Ranking sort order — by type**
    - **Validates: Requirements 11.1, 11.2**
    - Create `tests/test_ranking_service.py`
  - [ ]* 10.3 Write property test for ranking sort order — global (Property 12)
    - **Property 12: Ranking sort order — global**
    - **Validates: Requirements 12.1, 12.2**

- [x] 11. Implement `AnalyticsService` (ART-8)
  - [x] 11.1 Create `backend/app/services/analytics_service.py`
    - Implement `get_analytics(assessment_type=None)` — calls `repository.aggregate_analytics`, assembles `AnalyticsResult`
    - Build normalized score buckets (0–9, 10–19, … 90–100) from raw pipeline output
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [ ]* 11.2 Write property test for analytics aggregation correctness (Property 13)
    - **Property 13: Analytics aggregation correctness**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
    - Create `tests/test_analytics_service.py`

- [x] 12. Implement admin auth dependency and admin router (ART-7, ART-8, ART-9)
  - [x] 12.1 Add `get_admin_context` dependency to `backend/app/api/deps.py`
    - Validate a static admin token from settings (e.g. `settings.admin_token`) via `Authorization: Bearer` header
    - Raise `AppError(401, "UNAUTHORIZED")` when token is missing; `AppError(403, "FORBIDDEN")` when invalid
    - _Requirements: 9.1, 9.5_
  - [x] 12.2 Create `backend/app/api/routes/admin.py` with all five admin endpoints
    - `GET /admin/results` — paginated list using `AdminResultSummary`; filters `assessment_type`, `classification_value`; mask PII (return `student_id` only, no name/CPF)
    - `GET /admin/results/{id}` — detail using `AdminResultDetail` with `question_results`; return 404 `ASSESSMENT_NOT_FOUND` when missing
    - `GET /admin/analytics` — call `AnalyticsService.get_analytics`; optional `assessment_type` query param
    - `GET /admin/ranking/by-type` — call `RankingService.rank_by_type`; require `assessment_type` query param
    - `GET /admin/ranking/global` — call `RankingService.rank_global`
    - _Requirements: 9.1–9.6, 10.5, 11.3, 11.4, 12.3, 12.4_
  - [x] 12.3 Register admin router and inject new services in `main.py`
    - Import and include `admin_router` with prefix `/admin`
    - Instantiate `RankingService` and `AnalyticsService` in lifespan; attach to `request.state`
    - _Requirements: 9.1, 10.1, 11.3, 12.3_
  - [x] 12.4 Write example tests for admin API contracts
    - Add example tests for `assessment_type` and `classification_value` filters, 404 on missing assessment, and per-question detail response shape
    - Extend `tests/test_http_api.py`

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)` minimum
- All property tests are tagged with `# Feature: assessment-evaluation-engine, Property N: <text>`
- Stub repositories (no real DB) are used in all tests per project convention
