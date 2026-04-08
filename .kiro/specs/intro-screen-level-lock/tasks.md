# intro-screen-level-lock Tasks

## Tasks

- [x] 1. Exploratory tests (unfixed code)
  - [x] 1.1 Write a test that renders `LevelPicker` with `completedAssessments` containing `assessment_type: "geral"` and asserts the "Geral" button is disabled — expect this to FAIL on unfixed code
  - [x] 1.2 Write a test that renders `CompletedAssessmentsList` with the same input and asserts the list item label contains "Geral" — expect this to FAIL on unfixed code
  - [x] 1.3 Run the exploratory tests against the unfixed code and confirm both fail, validating the root cause hypothesis

- [x] 2. Apply the fix
  - [x] 2.1 In `LevelPicker`, change `(a) => a.level` to `(a) => a.assessment_type` when building `completedLevels`
  - [x] 2.2 In `CompletedAssessmentsList`, change `assessment.level` to `assessment.assessment_type` in both the `LEVEL_LABELS` lookup and the fallback expression

- [x] 3. Fix-checking tests (Property 1)
  - [x] 3.1 Verify the exploratory tests from task 1 now pass against the fixed code
  - [x] 3.2 Write tests for all remaining valid `assessment_type` values (`iniciante`, `junior`, `pleno`, `senior`) asserting each locks its corresponding button
  - [x] 3.3 Write a test asserting `CompletedAssessmentsList` renders the correct `LEVEL_LABELS` entry and formatted date for a completed assessment

- [x] 4. Preservation-checking tests (Property 2)
  - [x] 4.1 Write a test that renders `LevelPicker` with `completedAssessments = []` and asserts all five level buttons are enabled
  - [x] 4.2 Write a property-based test: for any random subset of valid level values used as `assessment_type`, exactly those buttons are disabled and the rest are enabled
  - [x] 4.3 Write a test that renders `CompletedAssessmentsList` with an empty array and asserts nothing is rendered
  - [x] 4.4 Write a test with an unknown `assessment_type` string and assert the raw string is used as the fallback label (no crash)
