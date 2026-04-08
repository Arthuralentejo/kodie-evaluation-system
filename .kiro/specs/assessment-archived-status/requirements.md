# Requirements Document

## Introduction

This feature exposes the `archived` status of completed assessments through the
`/assessments/current` endpoint and surfaces that information in the frontend
`IntroScreen`. Students who have completed an assessment and then started a new
one will see their previous assessments clearly marked as archived (superseded),
while the most recent valid assessment is highlighted as the active result. This
lets students understand at a glance which result is currently considered valid
and which ones were overridden.

## Glossary

- **Assessment**: A single exam attempt stored in MongoDB with fields `status`
  (`DRAFT` | `COMPLETED`) and `archived` (boolean).
- **Active Assessment**: The most recent `COMPLETED` assessment that has
  `archived: false`. There is at most one per student at any time.
- **Archived Assessment**: A `COMPLETED` assessment with `archived: true`,
  meaning it was superseded when the student started a new assessment.
- **CompletedAssessmentSummary**: The API response object representing one entry
  in the completed-assessments history list returned by `/assessments/current`.
- **IntroScreen**: The React screen shown after login, where the student chooses
  a level and sees their assessment history.
- **CompletedAssessmentsList**: The sub-component inside `IntroScreen` that
  renders the list of completed assessments.
- **Assessment_Service**: The backend service class `AssessmentService` that
  implements business logic for assessments.
- **Assessment_Repository**: The backend repository class `AssessmentRepository`
  that performs raw MongoDB operations.
- **API**: The FastAPI application exposing the `/assessments/current` endpoint.

---

## Requirements

### Requirement 1: Expose archived flag in the API response

**User Story:** As a student, I want the assessment history returned by the API
to tell me which assessments are archived, so that the frontend can distinguish
the active result from superseded ones.

#### Acceptance Criteria

1. THE `CompletedAssessmentSummary` SHALL include an `is_archived` boolean field.
2. WHEN `Assessment_Service` builds the completed-assessments list, THE
   `Assessment_Service` SHALL set `is_archived` to `true` for every assessment
   whose `archived` field is `true` in the database document.
3. WHEN `Assessment_Service` builds the completed-assessments list, THE
   `Assessment_Service` SHALL set `is_archived` to `false` for every assessment
   whose `archived` field is `false` in the database document.
4. THE `API` SHALL serialize `is_archived` as a JSON boolean in every object
   inside the `assessments` array of the `/assessments/current` response.

---

### Requirement 2: Identify the single active (non-archived) completed assessment

**User Story:** As a student, I want to know which of my completed assessments
is the currently valid one, so that I understand which result represents my
official standing.

#### Acceptance Criteria

1. WHEN a student has at least one completed assessment with `archived: false`,
   THE `Assessment_Service` SHALL include exactly one entry with `is_archived:
   false` in the `assessments` list.
2. WHEN a student has no completed assessment with `archived: false`, THE
   `Assessment_Service` SHALL return an `assessments` list where every entry has
   `is_archived: true` (or the list is empty).
3. WHEN a student has multiple completed assessments, THE `Assessment_Service`
   SHALL order the `assessments` list with the most recently completed assessment
   first (descending `completed_at`).

---

### Requirement 3: Display archived status in the IntroScreen

**User Story:** As a student, I want the IntroScreen to visually distinguish
archived assessments from the active one, so that I can immediately see which
result is valid.

#### Acceptance Criteria

1. WHEN `CompletedAssessmentsList` renders an assessment with `is_archived:
   false`, THE `CompletedAssessmentsList` SHALL display a label indicating the
   assessment is the active/valid result (pt-BR: "Válida" or equivalent).
2. WHEN `CompletedAssessmentsList` renders an assessment with `is_archived:
   true`, THE `CompletedAssessmentsList` SHALL display a label indicating the
   assessment is archived (pt-BR: "Arquivada").
3. THE `CompletedAssessmentsList` SHALL apply a distinct visual style (CSS
   class) to archived assessment items so they appear visually de-emphasized
   compared to the active one.
4. IF the `assessments` array is empty or absent, THE `CompletedAssessmentsList`
   SHALL render nothing (no list, no heading).
