# Design Document: Markdown Question Support

## Overview

This feature adds markdown rendering to the `QuestionsScreen` component so that question statements containing fenced code blocks and inline code are displayed with proper formatting and syntax highlighting. The change is purely frontend — the backend already stores and returns the `statement` field as-is. A new `MarkdownRenderer` component wraps `react-markdown` with `rehype-highlight` (syntax highlighting) and `rehype-sanitize` (XSS protection), and is dropped in place of the raw `<h1>` that currently renders the question statement.

The exam source files (`exam.jsonl` and `exam.md`) are also audited and corrected to ensure all code-bearing questions use valid fenced code block syntax with language identifiers.

## Architecture

The change is isolated to the frontend. No backend routes, models, or services are modified.

```
QuestionsScreen
  └── question-heading-card
        └── MarkdownRenderer          ← new component (replaces bare <h1>)
              ├── react-markdown
              ├── rehype-sanitize      ← strips disallowed HTML / XSS
              └── rehype-highlight     ← adds hljs CSS classes to <code> blocks
```

`MarkdownRenderer` is a pure presentational component: it receives a `content` string prop and returns rendered React nodes. It has no state and no side effects.

Styles for code blocks are added to `styles.css` under scoped class selectors. No inline styles or CSS-in-JS are introduced.

## Components and Interfaces

### `MarkdownRenderer` component

**File:** `frontend/src/components/MarkdownRenderer.jsx`

```jsx
// Props
{
  content: string   // raw markdown text (the question statement)
}
```

Renders `content` using `react-markdown` with the following rehype plugin pipeline:

1. `rehype-sanitize` — applied first to strip any disallowed HTML tags/attributes before highlight classes are added. Uses the default schema, which allows `class` attributes on `code` elements (required by rehype-highlight).
2. `rehype-highlight` — applied after sanitize; adds `hljs` and `language-*` classes to `<code>` elements inside fenced blocks.

The component wraps the output in a `<div className="markdown-body">` so that prose and code block styles can be scoped without affecting the rest of the UI.

### Integration into `QuestionsScreen`

In `QuestionsScreen.jsx`, the `question-heading-card` block currently renders:

```jsx
<div className="question-heading-card">
  <h1>{currentQuestion.statement}</h1>
</div>
```

This becomes:

```jsx
<div className="question-heading-card">
  <MarkdownRenderer content={currentQuestion.statement} />
</div>
```

The `<h1>` is removed; heading-level typography for the question statement is handled by the `.markdown-body` prose styles in `styles.css`.

### New npm dependencies

| Package | Role |
|---|---|
| `react-markdown` | Parses markdown and renders React components |
| `rehype-highlight` | Syntax highlighting via highlight.js CSS classes |
| `rehype-sanitize` | XSS sanitization of rendered HTML |
| `highlight.js` | Peer dependency of rehype-highlight; provides language grammars and a CSS theme |

## Data Models

No data model changes. The `statement` field on the question document is already a plain string; the backend returns it unchanged. The frontend now interprets that string as markdown instead of plain text.

### Exam data corrections (`exam.jsonl` / `exam.md`)

Questions that contain code snippets must use valid fenced code block syntax:

```
// Valid — triple backticks with language identifier
```python
x = 1
```

// Invalid — single backticks used as block (renders as inline code)
`x = 1`

// Invalid — fenced block without language identifier
```
x = 1
```
```

All questions in `exam.jsonl` that contain code are audited and updated to use the valid form. `exam.md` is updated to match.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Fenced code blocks produce `<pre><code>` elements

*For any* string containing a fenced code block (triple-backtick delimited), rendering it through `MarkdownRenderer` SHALL produce a DOM containing at least one `<pre>` element wrapping a `<code>` element.

**Validates: Requirements 1.1**

### Property 2: Inline code produces a `<code>` element outside `<pre>`

*For any* string containing at least one inline code span (single-backtick delimited), rendering it through `MarkdownRenderer` SHALL produce a DOM containing a `<code>` element that is not a descendant of a `<pre>` element.

**Validates: Requirements 1.2**

### Property 3: Plain text produces no code elements

*For any* string that contains no backtick characters, rendering it through `MarkdownRenderer` SHALL produce a DOM containing no `<pre>` or `<code>` elements.

**Validates: Requirements 1.3**

### Property 4: XSS payloads are stripped

*For any* string containing HTML injection payloads (e.g., `<script>`, `onerror=`, `javascript:` hrefs), rendering it through `MarkdownRenderer` SHALL produce a DOM containing no `<script>` elements and no event-handler attributes (`on*`).

**Validates: Requirements 1.5**

### Property 5: Supported languages receive an `hljs` class

*For any* fenced code block whose language identifier is one of `python`, `javascript`, `sql`, `bash`, `dockerfile`, `yaml`, rendering it through `MarkdownRenderer` SHALL produce a `<code>` element whose `className` includes `language-<lang>` (added by rehype-highlight).

**Validates: Requirements 2.1**

### Property 6: Unknown or missing language does not throw

*For any* fenced code block with no language identifier or an unrecognized language string, rendering it through `MarkdownRenderer` SHALL complete without throwing an error and SHALL produce a `<pre><code>` block in the DOM.

**Validates: Requirements 2.2**

### Property 7: Seeding preserves markdown statement content

*For any* question statement string (including strings containing fenced code blocks, inline code, and special characters), passing it through the `_build_row` seeding function SHALL produce a `Question` whose `statement` field is identical to the input string (after `.strip()`).

**Validates: Requirements 4.3**

### Property 8: All fenced code blocks in `exam.jsonl` have a language identifier

*For any* question in `exam.jsonl` whose `pergunta` field contains a fenced code block (triple-backtick fence), the opening fence line SHALL include a non-empty language identifier.

**Validates: Requirements 4.1**

## Error Handling

**Malformed markdown** — `react-markdown` is lenient by design; it never throws on malformed input. Unclosed backticks or malformed fences are rendered as plain text.

**Unrecognized language identifier** — `rehype-highlight` is configured with `ignoreMissing: true` so that an unknown language tag does not throw; the block is rendered without highlighting classes.

**XSS / unsafe HTML** — `rehype-sanitize` strips disallowed elements and attributes before the output reaches the DOM. The default sanitization schema is used, with the `class` attribute explicitly allowed on `code` and `span` elements so that highlight.js classes are preserved.

**Plugin ordering** — `rehype-sanitize` must run before `rehype-highlight` in the plugin array to avoid stripping the `hljs` classes added by the highlighter. The correct order is `[rehypeHighlight, rehypeSanitize]` — highlight first so classes are present, then sanitize with a schema that allows those classes. If the order is reversed, all highlighting classes are stripped.

> Note on plugin order: rehype-highlight adds `class` attributes; rehype-sanitize must be configured to allow `class` on `code`/`span` elements. The recommended approach is to run highlight first, then sanitize with a permissive-enough schema for `class`.

## Testing Strategy

### Unit / example-based tests

- Render `MarkdownRenderer` with a fenced Python code block → assert `<pre><code>` present.
- Render with inline code → assert `<code>` present, not inside `<pre>`.
- Render with plain text → assert no `<pre>` or `<code>` elements.
- Render each of the 6 supported languages → assert no error thrown and block renders.
- Render with `<script>alert(1)</script>` embedded in markdown → assert no `<script>` in DOM.

### Property-based tests

The project uses `@fast-check/vitest` (already in `devDependencies`). Each property test runs a minimum of 100 iterations.

**Property 1** — `fc.string()` filtered to contain at least one fenced code block pattern; assert `<pre><code>` in rendered output.
Tag: `Feature: markdown-question-support, Property 1: fenced code blocks produce pre>code elements`

**Property 2** — `fc.string()` filtered to contain at least one inline code span; assert `<code>` not inside `<pre>`.
Tag: `Feature: markdown-question-support, Property 2: inline code produces code element outside pre`

**Property 3** — `fc.string().filter(s => !s.includes('\`'))` (no backticks); assert no `<pre>` or `<code>` in rendered output.
Tag: `Feature: markdown-question-support, Property 3: plain text produces no code elements`

**Property 4** — `fc.constantFrom('<script>alert(1)</script>', '<img onerror=alert(1)>', ...)` combined with arbitrary surrounding text; assert no `<script>` or `on*` attributes in DOM.
Tag: `Feature: markdown-question-support, Property 4: XSS payloads are stripped`

**Property 5** — `fc.constantFrom('python', 'javascript', 'sql', 'bash', 'dockerfile', 'yaml')` used to build a fenced block; assert `<code>` className includes `language-<lang>`.
Tag: `Feature: markdown-question-support, Property 5: supported languages receive hljs class`

**Property 6** — `fc.string().filter(s => !['python','javascript','sql','bash','dockerfile','yaml'].includes(s))` as language identifier; assert no throw and `<pre><code>` present.
Tag: `Feature: markdown-question-support, Property 6: unknown or missing language does not throw`

**Property 7 (backend, Python/Hypothesis)** — `st.text()` as statement; pass through `_build_row` with a minimal valid question dict; assert `question.statement == statement.strip()`.
Tag: `Feature: markdown-question-support, Property 7: seeding preserves markdown statement content`

**Property 8** — Parse `exam.jsonl` in a test; for each question whose `pergunta` contains ` ``` `, assert the fence line matches ` ```<lang> ` where `<lang>` is non-empty.
Tag: `Feature: markdown-question-support, Property 8: all fenced code blocks in exam.jsonl have a language identifier`

### Integration / smoke checks

- Visual review of `QuestionsScreen` with a question containing a Python code block at desktop and mobile (375 px) viewports.
- Verify contrast ratio of the chosen highlight.js theme against the code block background meets WCAG 2.1 AA (4.5:1 minimum) via manual inspection or a browser contrast tool.
- Verify `MarkdownRenderer` source contains no `style=` prop or CSS-in-JS imports.
