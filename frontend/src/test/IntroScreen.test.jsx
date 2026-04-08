import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { IntroScreen } from '../components/screens/IntroScreen';

// Shared completed assessment fixture using the API shape (assessment_type, not level)
const completedGeral = [
  {
    assessment_id: 'abc123',
    assessment_type: 'geral',
    completed_at: '2024-01-15T10:00:00Z',
  },
];

// Default props that keep IntroScreen in a renderable state with the level picker visible.
// assessmentStatus must NOT be 'DRAFT' so canPickLevel is true and LevelPicker is rendered.
const baseProps = {
  assessmentStatus: 'COMPLETED',
  isBusy: false,
  onLogout: () => {},
  onStart: () => {},
  onBack: () => {},
  screenError: null,
  selectedLevel: 'iniciante',
  onLevelChange: () => {},
};

// Task 1.1 — LevelPicker: "Geral" button should be disabled when assessment_type: "geral" is completed
// This test is EXPECTED TO FAIL on unfixed code because LevelPicker reads a.level (undefined),
// so completedLevels is always empty and the button is never disabled.
describe('Task 1.1 — LevelPicker bug condition', () => {
  it('disables the "Geral" button when completedAssessments contains assessment_type: "geral"', () => {
    render(
      <IntroScreen
        {...baseProps}
        completedAssessments={completedGeral}
      />
    );

    // The "Geral" level button should be disabled
    const geralButton = screen.getByRole('button', { name: /geral/i });
    expect(geralButton).toBeDisabled();
  });
});

// Task 1.2 — CompletedAssessmentsList: label should contain "Geral" for assessment_type: "geral"
// This test is EXPECTED TO FAIL on unfixed code because CompletedAssessmentsList reads
// assessment.level (undefined), so LEVEL_LABELS[undefined] is undefined and the label is blank.
describe('Task 1.2 — CompletedAssessmentsList bug condition', () => {
  it('renders a list item whose label contains "Geral" for assessment_type: "geral"', () => {
    render(
      <IntroScreen
        {...baseProps}
        completedAssessments={completedGeral}
      />
    );

    // The completed assessments list item should have a level label span with "Geral"
    // On unfixed code, assessment.level is undefined so the span renders empty/undefined
    const levelSpan = document.querySelector(
      '.completed-assessment-item__level'
    );
    expect(levelSpan).toBeInTheDocument();
    expect(levelSpan).toHaveTextContent('Geral');
  });
});

// Task 3.2 — LevelPicker: each valid assessment_type locks its corresponding button
describe('Task 3.2 — LevelPicker locks each valid assessment_type', () => {
  const cases = [
    { assessment_type: 'iniciante', label: /iniciante/i },
    { assessment_type: 'junior', label: /júnior/i },
    { assessment_type: 'pleno', label: /pleno/i },
    { assessment_type: 'senior', label: /sênior/i },
  ];

  cases.forEach(({ assessment_type, label }) => {
    it(`disables the matching button when assessment_type is "${assessment_type}"`, () => {
      render(
        <IntroScreen
          {...baseProps}
          completedAssessments={[
            { assessment_id: 'x', assessment_type, completed_at: '2024-06-01T00:00:00Z' },
          ]}
        />
      );

      const button = screen.getByRole('button', { name: label });
      expect(button).toBeDisabled();
    });
  });
});

// Task 3.3 — CompletedAssessmentsList: renders correct LEVEL_LABELS entry and formatted date
describe('Task 3.3 — CompletedAssessmentsList renders label and date', () => {
  it('shows the Portuguese label and formatted date for a completed assessment', () => {
    const completedAt = '2024-03-20T14:30:00Z';
    render(
      <IntroScreen
        {...baseProps}
        completedAssessments={[
          { assessment_id: 'y', assessment_type: 'junior', completed_at: completedAt },
        ]}
      />
    );

    const levelSpan = document.querySelector('.completed-assessment-item__level');
    expect(levelSpan).toBeInTheDocument();
    expect(levelSpan).toHaveTextContent('Júnior');

    const dateSpan = document.querySelector('.completed-assessment-item__date');
    expect(dateSpan).toBeInTheDocument();
    // formatDatePtBR uses pt-BR locale: dd/mm/yyyy
    const formatted = new Date(completedAt).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
    expect(dateSpan).toHaveTextContent(formatted);
  });
});

// ─── Task 4: Preservation-checking tests (Property 2) ───────────────────────

// Task 4.1 — LevelPicker with empty completedAssessments: all five buttons enabled
describe('Task 4.1 — LevelPicker with empty completedAssessments', () => {
  it('enables all five level buttons when completedAssessments is []', () => {
    render(
      <IntroScreen
        {...baseProps}
        completedAssessments={[]}
      />
    );

    const buttons = [
      screen.getByRole('button', { name: /iniciante/i }),
      screen.getByRole('button', { name: /júnior/i }),
      screen.getByRole('button', { name: /pleno/i }),
      screen.getByRole('button', { name: /sênior/i }),
      screen.getByRole('button', { name: /geral/i }),
    ];

    buttons.forEach((btn) => expect(btn).not.toBeDisabled());
  });
});

// Task 4.2 — Property-based test (manual, all 2^5 subsets of valid level values)
// For any subset of valid assessment_type values, exactly those buttons are disabled
// and the rest are enabled.
// Validates: Requirements 3.1
describe('Task 4.2 — Property: for any subset of valid levels, exactly those buttons are disabled', () => {
  const VALID_LEVELS = ['iniciante', 'junior', 'pleno', 'senior', 'geral'];

  // Map each level value to the accessible name regex used by the button
  const LEVEL_LABEL_REGEX = {
    iniciante: /iniciante/i,
    junior: /júnior/i,
    pleno: /pleno/i,
    senior: /sênior/i,
    geral: /geral/i,
  };

  // Generate all 2^5 = 32 subsets
  const allSubsets = [];
  for (let mask = 0; mask < 1 << VALID_LEVELS.length; mask++) {
    const subset = VALID_LEVELS.filter((_, i) => (mask >> i) & 1);
    allSubsets.push(subset);
  }

  allSubsets.forEach((subset) => {
    const label = subset.length === 0 ? '(empty)' : subset.join(', ');
    it(`subset [${label}]: exactly those buttons are disabled`, () => {
      const completedAssessments = subset.map((lvl, i) => ({
        assessment_id: `id-${i}`,
        assessment_type: lvl,
        completed_at: '2024-01-01T00:00:00Z',
      }));

      const { unmount } = render(
        <IntroScreen
          {...baseProps}
          completedAssessments={completedAssessments}
        />
      );

      const completedSet = new Set(subset);

      VALID_LEVELS.forEach((lvl) => {
        const btn = screen.getByRole('button', { name: LEVEL_LABEL_REGEX[lvl] });
        if (completedSet.has(lvl)) {
          expect(btn, `expected "${lvl}" button to be disabled`).toBeDisabled();
        } else {
          expect(btn, `expected "${lvl}" button to be enabled`).not.toBeDisabled();
        }
      });

      unmount();
    });
  });
});

// Task 4.3 — CompletedAssessmentsList with empty array renders nothing
describe('Task 4.3 — CompletedAssessmentsList with empty array', () => {
  it('renders nothing when completedAssessments is []', () => {
    render(
      <IntroScreen
        {...baseProps}
        completedAssessments={[]}
      />
    );

    // No list items should be present
    const items = document.querySelectorAll('.completed-assessment-item');
    expect(items).toHaveLength(0);

    // The container itself should not be rendered
    const container = document.querySelector('.completed-assessments');
    expect(container).not.toBeInTheDocument();
  });
});

// Task 4.4 — Unknown assessment_type uses raw string as fallback label (no crash)
describe('Task 4.4 — Unknown assessment_type falls back to raw string', () => {
  it('shows the raw "especialista" string as the level label without crashing', () => {
    render(
      <IntroScreen
        {...baseProps}
        completedAssessments={[
          {
            assessment_id: 'z1',
            assessment_type: 'especialista',
            completed_at: '2024-05-10T08:00:00Z',
          },
        ]}
      />
    );

    const levelSpan = document.querySelector('.completed-assessment-item__level');
    expect(levelSpan).toBeInTheDocument();
    expect(levelSpan).toHaveTextContent('especialista');
  });
});

// ─── Tasks 7.2 & 7.3: Property-based tests (fast-check) ─────────────────────

import { test } from '@fast-check/vitest';
import * as fc from 'fast-check';

// Shared generator for tasks 7.2 and 7.3
const assessmentArb = fc.array(
  fc.record({
    assessment_id: fc.uuid(),
    assessment_type: fc.constantFrom('iniciante', 'junior', 'pleno', 'senior', 'geral'),
    completed_at: fc.constant('2024-01-01T00:00:00Z'),
    is_archived: fc.boolean(),
  }),
  { minLength: 1 }
);

// Feature: assessment-archived-status, Property 3: status label matches is_archived value
// Validates: Requirements 3.1, 3.2
describe('Property 3 — status label matches is_archived value', () => {
  test.prop([assessmentArb])('status span shows "Válida" or "Arquivada" based on is_archived', (assessments) => {
    const { unmount } = render(
      <IntroScreen
        {...baseProps}
        completedAssessments={assessments}
      />
    );

    const items = document.querySelectorAll('.completed-assessment-item');
    expect(items).toHaveLength(assessments.length);

    assessments.forEach((assessment, i) => {
      const statusSpan = items[i].querySelector('.completed-assessment-item__status');
      expect(statusSpan).not.toBeNull();
      if (assessment.is_archived) {
        expect(statusSpan.textContent).toBe('Arquivada');
      } else {
        expect(statusSpan.textContent).toBe('Válida');
      }
    });

    unmount();
  });
});

// Feature: assessment-archived-status, Property 4: archived CSS class applied iff is_archived is true
// Validates: Requirements 3.3
describe('Property 4 — archived CSS class applied iff is_archived is true', () => {
  test.prop([assessmentArb])('li has completed-assessment-item--archived iff is_archived is true', (assessments) => {
    const { unmount } = render(
      <IntroScreen
        {...baseProps}
        completedAssessments={assessments}
      />
    );

    const items = document.querySelectorAll('.completed-assessment-item');
    expect(items).toHaveLength(assessments.length);

    assessments.forEach((assessment, i) => {
      const li = items[i];
      if (assessment.is_archived) {
        expect(li.classList.contains('completed-assessment-item--archived')).toBe(true);
      } else {
        expect(li.classList.contains('completed-assessment-item--archived')).toBe(false);
      }
    });

    unmount();
  });
});
