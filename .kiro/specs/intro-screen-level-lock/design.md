# intro-screen-level-lock Bugfix Design

## Overview

After a student completes any assessment, the `IntroScreen` should lock the corresponding level in `LevelPicker` and display it in `CompletedAssessmentsList`. Instead, both components silently read `a.level` — a field that does not exist on the API response — so the completed-levels set is always empty and the list always renders nothing.

The fix is a single-line normalization in `IntroScreen.jsx`: replace every read of `a.level` with `a.assessment_type`, which is the actual field name returned by `GET /assessments/current` via `CompletedAssessmentSummary`.

No backend changes are required.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — `completedAssessments` contains at least one item and the code reads `a.level` instead of `a.assessment_type`
- **Property (P)**: The desired behavior — the level button matching `a.assessment_type` is disabled and the label in the list resolves correctly
- **Preservation**: All behaviors unrelated to reading the completed-level field must remain unchanged
- **`LevelPicker`**: Component in `IntroScreen.jsx` that renders one button per level and disables buttons whose value is in `completedLevels`
- **`CompletedAssessmentsList`**: Component in `IntroScreen.jsx` that renders the history of completed assessments with level label and date
- **`completedAssessments`**: Prop passed from `useAssessmentFlow` — an array of `CompletedAssessmentSummary` objects with shape `{ assessment_id, assessment_type, completed_at }`
- **`assessment_type`**: The field name used by the API (and the backend model `CompletedAssessmentSummary`) to identify the level of a completed assessment

## Bug Details

### Bug Condition

The bug manifests whenever `completedAssessments` is non-empty. Both `LevelPicker` and `CompletedAssessmentsList` iterate over the array and read `a.level`, which is `undefined` for every item because the API returns `a.assessment_type`. The resulting `completedLevels` set is always empty, so no button is ever disabled and no label ever resolves.

**Formal Specification:**
```
FUNCTION isBugCondition(completedAssessments)
  INPUT: completedAssessments — array of assessment summary objects from the API
  OUTPUT: boolean

  RETURN completedAssessments.length > 0
         AND completedAssessments[0].level IS undefined
         AND completedAssessments[0].assessment_type IS NOT undefined
END FUNCTION
```

### Examples

- Student completes "Geral" → API returns `[{ assessment_type: "geral", ... }]` → `completedLevels` = `{}` (empty) → "Geral" button is enabled (bug)
- Student completes "Júnior" → API returns `[{ assessment_type: "junior", ... }]` → list renders `LEVEL_LABELS[undefined]` = `undefined` → label is blank (bug)
- Student has no completed assessments → `completedAssessments = []` → `completedLevels` = `{}` → all buttons enabled (correct, no bug)
- After fix: `completedLevels` = `{ "geral" }` → "Geral" button is disabled and list shows "Geral · dd/mm/yyyy" (correct)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Mouse clicks on enabled level buttons must continue to work exactly as before
- The `assessmentStatus === 'DRAFT'` path must continue to skip the level picker entirely
- The override confirmation modal must continue to appear when `hasActiveAssessment` is true
- All other keyboard/mouse interactions with the screen must remain unchanged

**Scope:**
All code paths that do NOT involve reading `a.level` from `completedAssessments` are completely unaffected. This includes:
- The `onStart` / `startAssessment` flow
- The `assessmentStatus` guard (`canPickLevel`)
- The `OverrideConfirmModal` logic
- The `useAssessmentFlow` hook (no changes needed there)

## Hypothesized Root Cause

The field name mismatch was introduced when the backend model was defined with `assessment_type` but the frontend was written (or copied) using `level` — a name that appears in the `LEVELS` constant array but is never present on API response objects.

1. **Wrong field name in `LevelPicker`**: `(completedAssessments || []).map((a) => a.level)` should be `a.assessment_type`
2. **Wrong field name in `CompletedAssessmentsList`**: `LEVEL_LABELS[assessment.level]` should be `LEVEL_LABELS[assessment.assessment_type]`, and the fallback `|| assessment.level` should be `|| assessment.assessment_type`

There are exactly two occurrences in `IntroScreen.jsx`. No other file reads `a.level` from completed assessments.

## Correctness Properties

Property 1: Bug Condition - Completed Level Is Locked in LevelPicker

_For any_ `completedAssessments` array where `isBugCondition` holds (array is non-empty and items carry `assessment_type`), the fixed `LevelPicker` SHALL disable the button whose `value` equals `assessment_type` and leave all other buttons enabled.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Empty Completed Assessments Leaves All Levels Enabled

_For any_ `completedAssessments` array where `isBugCondition` does NOT hold (array is empty), the fixed `LevelPicker` SHALL produce the same result as the original — all five level buttons enabled — preserving the no-history experience.

**Validates: Requirements 3.1**

## Fix Implementation

### Changes Required

**File**: `frontend/src/components/screens/IntroScreen.jsx`

**Change 1 — `LevelPicker` (line ~67)**

Replace:
```js
const completedLevels = new Set(
  (completedAssessments || []).map((a) => a.level)
);
```
With:
```js
const completedLevels = new Set(
  (completedAssessments || []).map((a) => a.assessment_type)
);
```

**Change 2 — `CompletedAssessmentsList` (line ~107)**

Replace:
```jsx
{LEVEL_LABELS[assessment.level] || assessment.level}
```
With:
```jsx
{LEVEL_LABELS[assessment.assessment_type] || assessment.assessment_type}
```

No other files need to change. The `useAssessmentFlow` hook already stores the raw API array in `completedAssessments` and passes it through correctly.

## Testing Strategy

### Validation Approach

Two-phase approach: first run exploratory tests against the unfixed code to confirm the root cause, then verify the fix satisfies both correctness properties.

### Exploratory Bug Condition Checking

**Goal**: Confirm that reading `a.level` on the unfixed code produces an empty set and that buttons are never disabled.

**Test Plan**: Render `LevelPicker` with a `completedAssessments` prop containing items with `assessment_type: "geral"` and assert the "Geral" button is disabled. Run on unfixed code — the assertion will fail, confirming the bug.

**Test Cases**:
1. **Geral locked test**: `completedAssessments = [{ assessment_id: "x", assessment_type: "geral", completed_at: "..." }]` → assert "Geral" button has `disabled` attribute (fails on unfixed code)
2. **Label render test**: same input → assert list item text contains "Geral" (fails on unfixed code — renders blank)
3. **Multiple levels test**: two completed assessments with `assessment_type: "junior"` and `"pleno"` → assert both buttons disabled (fails on unfixed code)

**Expected Counterexamples**:
- "Geral" button is enabled despite completed assessment in the array
- Possible cause: `a.level` is `undefined`, so `completedLevels.has("geral")` is always `false`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed components produce the expected behavior.

**Pseudocode:**
```
FOR ALL completedAssessments WHERE isBugCondition(completedAssessments) DO
  render LevelPicker with completedAssessments
  FOR EACH a IN completedAssessments DO
    ASSERT button[a.assessment_type].disabled === true
  END FOR
  render CompletedAssessmentsList with completedAssessments
  FOR EACH a IN completedAssessments DO
    ASSERT listItem contains LEVEL_LABELS[a.assessment_type]
  END FOR
END FOR
```

### Preservation Checking

**Goal**: Verify that when `completedAssessments` is empty, the fixed code behaves identically to the original.

**Pseudocode:**
```
FOR ALL completedAssessments WHERE NOT isBugCondition(completedAssessments) DO
  ASSERT LevelPicker_original(completedAssessments) = LevelPicker_fixed(completedAssessments)
END FOR
```

**Testing Approach**: Property-based testing is well-suited here because:
- It generates many random `completedAssessments` arrays (including empty, single-item, multi-item)
- It catches edge cases like duplicate `assessment_type` values or unknown type strings
- It provides strong guarantees that the fix doesn't break the no-history path

**Test Cases**:
1. **Empty array preservation**: `completedAssessments = []` → all 5 buttons enabled, list renders nothing
2. **Unknown type preservation**: `assessment_type: "unknown_level"` → no button disabled (no matching value), list shows raw string as fallback
3. **DRAFT status preservation**: `assessmentStatus = "DRAFT"` → level picker section not rendered at all

### Unit Tests

- Render `LevelPicker` with each valid `assessment_type` value and assert the matching button is disabled
- Render `CompletedAssessmentsList` with a completed assessment and assert the correct `LEVEL_LABELS` entry is shown
- Render `LevelPicker` with empty `completedAssessments` and assert all buttons are enabled

### Property-Based Tests

- Generate random subsets of `LEVELS` values as `assessment_type` entries and verify exactly those buttons are disabled
- Generate random `completedAssessments` arrays and verify `completedLevels` equals the set of `assessment_type` values
- Verify that for any input, buttons NOT in `completedLevels` remain enabled

### Integration Tests

- Full flow: authenticate → load `completedAssessments` from mocked API → render `IntroScreen` → assert completed level is locked
- Verify `CompletedAssessmentsList` renders correct label and formatted date for each level
- Verify switching from `COMPLETED` status back to intro screen shows the locked level correctly
