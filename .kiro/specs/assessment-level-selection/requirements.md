# Requirements Document

## Introduction

This document defines the requirements for the **assessment-level-selection** feature of the Kodie platform. The feature extends the assessment flow so that students can choose a difficulty level (`iniciante`, `junior`, `pleno`, `senior`, or `geral`) before starting an assessment.

A student always has **at most one active (non-archived) assessment** across all levels at any time. When a student picks a different level, their current active assessment is archived and a new DRAFT is created at the new level. Completed levels are permanently locked — a level is locked if it appears anywhere in the student's completed history, including archived completed assessments.

Students are identified in assessment documents by an application-level `student_id` field (a ULID), decoupled from the MongoDB `_id` (ObjectId). Questions are filtered by exact category match at the database level — there is no cumulative level pooling.

The feature touches the backend domain model, question-selection logic, REST API, and the frontend Introduction screen.

---

## Glossary

- **AssessmentService**: The backend service layer responsible for all assessment business logic.
- **AssessmentRepository**: The backend data-access layer responsible for MongoDB operations on assessment documents.
- **QuestionSelector**: The function `build_assigned_question_ids` that selects questions for a new assessment.
- **IntroScreen**: The frontend React component that renders the introduction/level-selection screen.
- **Hook**: The `useAssessmentFlow` React hook that manages all frontend application state.
- **Level**: One of the five difficulty tiers — `iniciante`, `junior`, `pleno`, `senior`, `geral`.
- **DRAFT**: An assessment that has been started but not yet submitted.
- **COMPLETED**: An assessment that has been fully submitted and is permanently locked.
- **Active assessment**: The single non-archived assessment for a student (DRAFT or COMPLETED). At most one exists per student at any time.
- **Archived assessment**: An assessment with `archived=true`. It has been superseded because the student moved to a different level. Archived assessments are excluded from active queries but preserved in completed history.
- **Completed history**: All COMPLETED assessments for a student, including archived ones. Used for level-lock checks and history display.
- **Level picker**: The UI control on the IntroScreen that lets a student select a Level before starting.
- **student_id**: An application-level ULID string stored on the student document and referenced by assessment documents. Decoupled from the MongoDB `_id` (ObjectId).
- **Figma**: The external design tool used to maintain the product's visual specification (https://www.figma.com/design/zSYPF89omQ51ZuPKPyuBZw/Evaluation-System?node-id=0-1&m=dev).

---

## Requirements

### Requirement 1: Assessment Level Domain Model

**User Story:** As a platform architect, I want the Assessment document to carry a `level` field and an `archived` flag, so that each assessment is unambiguously associated with a difficulty tier and the one-active-assessment invariant can be enforced.

#### Acceptance Criteria

1. THE AssessmentService SHALL recognise exactly five valid level values: `iniciante`, `junior`, `pleno`, `senior`, and `geral`.
2. WHEN an Assessment document is created, THE AssessmentRepository SHALL persist the `level` field and `archived: false` on the document. The `level` field SHALL be one of `iniciante | junior | pleno | senior | geral`.
3. WHEN an Assessment document that has no `level` field is read, THE AssessmentService SHALL treat its level as `"iniciante"`.
4. WHEN an Assessment document that has no `archived` field is read, THE AssessmentService SHALL treat it as `archived: false`.
5. THE AssessmentRepository SHALL receive the MongoDB collection object at construction time and SHALL use `self.collection` for all operations, rather than resolving the collection per method call.

---

### Requirement 2: Student Identity — Application-Level ULID

**User Story:** As a platform architect, I want students to be identified by an application-level ULID field (`student_id`) rather than the MongoDB ObjectId, so that identity is decoupled from the storage layer.

#### Acceptance Criteria

1. THE seed script SHALL generate a `student_id` ULID for each student using `python-ulid` (`from ulid import ULID; str(ULID())`) and store it on the student document alongside `_id`.
2. WHEN an Assessment document is created, THE AssessmentRepository SHALL store the student's `student_id` ULID string on the document, not the MongoDB `_id`.
3. THE JWT auth context SHALL carry the `student_id` ULID as the subject claim; THE AssessmentService SHALL pass this ULID directly to the repository without resolving the MongoDB `_id`.
4. THE AssessmentRepository SHALL define a unique index on `{ student_id: 1 }` on the students collection to support O(1) ULID lookups.

---

### Requirement 3: Question Selection by Exact Level

**User Story:** As a student, I want the questions in my assessment to match exactly the difficulty level I chose, so that the evaluation is appropriate for my experience.

#### Acceptance Criteria

1. WHEN `list_questions_for_level` is called with a given level, THE AssessmentRepository SHALL pass `{ category: level }` as the filter to MongoDB — no in-Python category filtering is performed.
2. WHEN `build_assigned_question_ids` is called, THE QuestionSelector SHALL return only question IDs from the pre-filtered pool provided by `list_questions_for_level`, all of which have `category` exactly equal to the requested level.
3. THE QuestionSelector SHALL return at most `assessment_question_count` question IDs.
4. IF the filtered question pool for the chosen level contains no questions, THEN THE AssessmentService SHALL raise an error with HTTP status 409 and code `NO_QUESTIONS_FOR_LEVEL` with the message "Não há questões disponíveis para o nível selecionado."
5. WHEN `level` is `geral`, THE AssessmentRepository SHALL call `list_questions_for_geral()` (no category filter) instead of `list_questions_for_level(level)`, and THE QuestionSelector SHALL call `build_geral_question_ids(question_docs)` instead of `build_assigned_question_ids`.
6. WHEN `build_geral_question_ids` is called, THE QuestionSelector SHALL distribute `assessment_question_count` questions equally across the four categories (`iniciante`, `junior`, `pleno`, `senior`): `per_category = assessment_question_count // 4` questions per category, with the remainder distributed round-robin starting from `iniciante`. The total returned SHALL be at most `assessment_question_count`.
7. IF any of the four categories has no questions when `level` is `geral`, THE AssessmentService SHALL raise an error with HTTP status 409 and code `NO_QUESTIONS_FOR_LEVEL`.

---

### Requirement 4: One Active Assessment at a Time

**User Story:** As a student, I want to be able to switch levels freely before completing an assessment, so that I can start over at a different difficulty without being blocked by an old draft.

#### Acceptance Criteria

1. WHEN a student sends `POST /assessments` with a valid `level` and has no active assessment and no completed history at that level, THE AssessmentService SHALL create a new DRAFT at that level and return `{ assessment_id, status: "DRAFT", level }`.
2. WHEN a student sends `POST /assessments` for a level at which they already have an active DRAFT, THE AssessmentService SHALL return the existing DRAFT's `assessment_id` without creating or modifying any document (idempotent).
3. WHEN a student sends `POST /assessments` with a level that differs from their current active assessment's level, THE AssessmentService SHALL set `archived=true` on the current active assessment and then create a new DRAFT at the requested level.
4. WHEN `POST /assessments` is called with an unrecognised `level` value, THE API SHALL return HTTP 422.
5. AFTER any call to `create_assessment` that results in a new DRAFT being created, THE AssessmentRepository SHALL contain exactly one non-archived assessment for that student across all levels.

---

### Requirement 5: Completed Level Lock — Full History Including Archived

**User Story:** As a platform operator, I want completed levels to be permanently locked regardless of whether the completed assessment was later archived, so that students cannot redo a level they have already finished.

#### Acceptance Criteria

1. WHEN a student sends `POST /assessments` for a level that appears in their completed history — including archived COMPLETED assessments — THE AssessmentService SHALL return HTTP 409 with code `LEVEL_ALREADY_COMPLETED` and the message "Este nível já foi concluído e não pode ser iniciado novamente." No document is created or modified.
2. THE AssessmentService SHALL check completed history before checking the active assessment in `create_assessment`: first query fetches all COMPLETED assessments (including archived) for the level-lock check; second query fetches the active (non-archived) assessment.
3. WHEN a `DuplicateKeyError` occurs due to a concurrent `POST /assessments` for the same student and level, THE AssessmentRepository SHALL catch the error and return the existing DRAFT document.

---

### Requirement 6: Get Current Assessment Summary

**User Story:** As a student, I want the introduction screen to show me which levels I have already completed and whether I have an active assessment, so that I can make an informed choice about what to do next.

#### Acceptance Criteria

1. WHEN `GET /assessments/current` is called and the student has no assessments, THE AssessmentService SHALL return `{ status: "NONE", assessment_id: null, level: null, completed_at: null, assessments: [] }`.
2. WHEN `GET /assessments/current` is called and the student has an active (non-archived) assessment, THE AssessmentService SHALL return the active assessment's `status`, `assessment_id`, `level`, and `completed_at` in the top-level fields.
3. WHEN `GET /assessments/current` is called, THE AssessmentService SHALL include ALL COMPLETED assessments for the student — including archived ones — in the `assessments` array, each entry containing `assessment_id`, `level`, and `completed_at`.
4. THE AssessmentService SHALL return the `assessments` array sorted by `completed_at` descending (most recent first).
5. WHEN a student has no active assessment but has completed history, THE AssessmentService SHALL return `status: "NONE"` in the top-level fields while still returning the non-empty `assessments` array.
6. THE AssessmentService SHALL use exactly two queries in `get_current_assessment`: one call to `find_active_assessment_by_student` (non-archived) and one call to `find_all_completed_assessments_by_student` (all COMPLETED including archived).

---

### Requirement 7: MongoDB Indexes

**User Story:** As a platform engineer, I want the database to enforce the one-active-assessment invariant and support efficient lookups, so that data integrity is guaranteed even under concurrent requests.

#### Acceptance Criteria

1. THE AssessmentRepository SHALL define a unique partial index on `{ student_id: 1 }` with `partialFilterExpression: { archived: { $ne: true } }` to enforce that at most one non-archived assessment exists per student at any time.
2. THE AssessmentRepository SHALL define a compound index on `{ student_id: 1, status: 1, completed_at: -1 }` to support efficient completed-history lookups.

---

### Requirement 8: Frontend Level Picker

**User Story:** As a student, I want to see a visual level picker on the introduction screen, so that I can select my desired difficulty level before starting the assessment.

#### Acceptance Criteria

1. WHEN the IntroScreen renders and `assessmentStatus` is not `"DRAFT"`, THE IntroScreen SHALL display a level picker containing one selectable option for each of the five levels: `iniciante`, `junior`, `pleno`, `senior`, and `geral`.
2. WHEN a student selects a level in the picker, THE IntroScreen SHALL visually highlight the selected level to indicate the current selection.
3. WHEN a level is present in `completedAssessments` (which includes archived completed assessments), THE IntroScreen SHALL render that level's picker option as disabled and display a "Concluído" badge on it.
4. WHEN the student clicks "Iniciar avaliação", THE IntroScreen SHALL invoke `onStart` and THE Hook SHALL send the `selectedLevel` value in the body of `POST /assessments`.
5. WHILE `isBusy` is true OR no level is selected OR the selected level is already present in `completedAssessments`, THE IntroScreen SHALL keep the "Iniciar avaliação" button disabled.

---

### Requirement 9: Frontend Completed Assessments List

**User Story:** As a student, I want to see a summary of my previously completed assessments on the introduction screen, so that I know which levels I have already finished.

#### Acceptance Criteria

1. WHEN `completedAssessments` contains one or more entries, THE IntroScreen SHALL render a completed assessments list displaying the level name and completion date for every entry.
2. WHEN `completedAssessments` is empty, THE IntroScreen SHALL not render the completed assessments list.

---

### Requirement 10: useAssessmentFlow Hook — Level State Management

**User Story:** As a developer, I want the `useAssessmentFlow` hook to manage level selection state and communicate it to the API, so that the IntroScreen remains a stateless presentational component.

#### Acceptance Criteria

1. WHEN `loadCurrentAssessment` receives an API response, THE Hook SHALL populate the `completedAssessments` state from the `assessments` field of the response (which includes all COMPLETED assessments, archived or not).
2. WHEN `startAssessment` is called, THE Hook SHALL include the current `selectedLevel` value in the `POST /assessments` request body.
3. WHEN `POST /assessments` returns successfully, THE Hook SHALL set `assessmentLevel` and `assessmentId` from the response and transition the application stage to `QUESTIONS`.
4. WHEN `POST /assessments` returns HTTP 409 with code `LEVEL_ALREADY_COMPLETED`, THE Hook SHALL surface the error to the UI without changing the application stage.

---

### Requirement 11: Figma Design Update

**User Story:** As a product designer, I want the Figma design file to reflect the implemented UI after frontend development is complete, so that the design source of truth stays in sync with the product.

#### Acceptance Criteria

1. WHEN frontend UI development for this feature is complete, THE Team SHALL update the Figma design at `https://www.figma.com/design/zSYPF89omQ51ZuPKPyuBZw/Evaluation-System?node-id=0-1&m=dev` to reflect the level picker and completed assessments list screens.
