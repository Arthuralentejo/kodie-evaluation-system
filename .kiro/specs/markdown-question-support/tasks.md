# Implementation Plan: Markdown Question Support

## Overview

Add markdown rendering with syntax highlighting to `QuestionsScreen`, introduce a `MarkdownRenderer` component backed by `react-markdown` + `rehype-highlight` + `rehype-sanitize`, update exam source data to use valid fenced code block syntax, and verify correctness with property-based and unit tests.

## Tasks

- [x] 1. Install frontend dependencies
  - Run `npm install react-markdown rehype-highlight rehype-sanitize highlight.js` inside `frontend/`
  - Verify the packages appear in `frontend/package.json` under `dependencies`
  - _Requirements: 1.4, 1.5, 2.1_

- [x] 2. Create `MarkdownRenderer` component
  - [x] 2.1 Implement `frontend/src/components/MarkdownRenderer.jsx`
    - Accept a single `content` string prop
    - Configure `react-markdown` with rehype plugin pipeline: `[rehypeHighlight, rehypeSanitize]` (highlight first, then sanitize with a schema that allows `class` on `code`/`span`)
    - Pass `{ ignoreMissing: true }` to `rehypeHighlight` so unknown language tags do not throw
    - Wrap output in `<div className="markdown-body">`
    - _Requirements: 1.4, 1.5, 2.1, 2.2_

  - [ ]* 2.2 Write property test for fenced code blocks produce `<pre><code>` elements
    - **Property 1: Fenced code blocks produce `<pre><code>` elements**
    - **Validates: Requirements 1.1**
    - Use `@fast-check/vitest`; generate strings containing at least one triple-backtick fence; assert rendered DOM contains `<pre>` wrapping `<code>`
    - Tag: `Feature: markdown-question-support, Property 1`

  - [ ]* 2.3 Write property test for inline code produces `<code>` outside `<pre>`
    - **Property 2: Inline code produces a `<code>` element outside `<pre>`**
    - **Validates: Requirements 1.2**
    - Generate strings with at least one single-backtick span; assert `<code>` present and not a descendant of `<pre>`
    - Tag: `Feature: markdown-question-support, Property 2`

  - [ ]* 2.4 Write property test for plain text produces no code elements
    - **Property 3: Plain text produces no code elements**
    - **Validates: Requirements 1.3**
    - Generate strings with no backtick characters; assert no `<pre>` or `<code>` in rendered output
    - Tag: `Feature: markdown-question-support, Property 3`

  - [ ]* 2.5 Write property test for XSS payloads are stripped
    - **Property 4: XSS payloads are stripped**
    - **Validates: Requirements 1.5**
    - Use `fc.constantFrom` with known XSS payloads combined with arbitrary surrounding text; assert no `<script>` elements and no `on*` attributes in DOM
    - Tag: `Feature: markdown-question-support, Property 4`

  - [ ]* 2.6 Write property test for supported languages receive `hljs` class
    - **Property 5: Supported languages receive an `hljs` class**
    - **Validates: Requirements 2.1**
    - Use `fc.constantFrom('python', 'javascript', 'sql', 'bash', 'dockerfile', 'yaml')` to build fenced blocks; assert `<code>` className includes `language-<lang>`
    - Tag: `Feature: markdown-question-support, Property 5`

  - [ ]* 2.7 Write property test for unknown or missing language does not throw
    - **Property 6: Unknown or missing language does not throw**
    - **Validates: Requirements 2.2**
    - Generate language identifiers not in the supported set; assert no error thrown and `<pre><code>` present in DOM
    - Tag: `Feature: markdown-question-support, Property 6`

- [x] 3. Add styles for markdown rendering
  - In `frontend/src/styles.css`, add styles scoped to `.markdown-body`:
    - Import a `highlight.js` theme (e.g., `github-dark`) via CSS `@import` or copy theme tokens as CSS variables
    - Style `pre` and `code` blocks: monospace font, preserved whitespace, distinct background, border, `overflow-x: auto` for horizontal scroll
    - Style inline `code` distinct from surrounding prose
    - Ensure `font-size` and scroll behavior remain readable at viewports < 768px
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Integrate `MarkdownRenderer` into `QuestionsScreen`
  - In `frontend/src/components/screens/QuestionsScreen.jsx`, replace the `<h1>{currentQuestion.statement}</h1>` inside `question-heading-card` with `<MarkdownRenderer content={currentQuestion.statement} />`
  - Import `MarkdownRenderer` at the top of the file
  - Remove the `<h1>` wrapper; heading-level typography is now handled by `.markdown-body` styles
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5. Checkpoint — ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Audit and fix exam source data
  - [x] 6.1 Update `backend/scripts/exam.jsonl`
    - Identify all questions whose `pergunta` field contains code snippets
    - Replace any single-backtick block usage or fenced blocks without a language identifier with valid triple-backtick fences including a language identifier (`python`, `javascript`, `sql`, `bash`, `dockerfile`, or `yaml`)
    - _Requirements: 4.1_

  - [x] 6.2 Update `assets/exam.md` to match `exam.jsonl`
    - Apply the same fenced code block corrections to `assets/exam.md` so both files are consistent
    - _Requirements: 4.2_

  - [ ]* 6.3 Write property test for all fenced code blocks in `exam.jsonl` have a language identifier
    - **Property 8: All fenced code blocks in `exam.jsonl` have a language identifier**
    - **Validates: Requirements 4.1**
    - Parse `exam.jsonl` in a Vitest test; for each question whose `pergunta` contains a triple-backtick fence, assert the opening fence line matches `` ```<lang> `` where `<lang>` is non-empty
    - Tag: `Feature: markdown-question-support, Property 8`

- [x] 7. Verify seeding preserves markdown content
  - [x] 7.1 Inspect `backend/scripts/seed_questions.py` `_build_row` function
    - Confirm the `statement` field is assigned directly from the source without modification or escaping
    - If any transformation is applied, remove it so the raw markdown string is preserved
    - _Requirements: 4.3_

  - [ ]* 7.2 Write property test for seeding preserves markdown statement content
    - **Property 7: Seeding preserves markdown statement content**
    - **Validates: Requirements 4.3**
    - Use `hypothesis` (`st.text()`) as the statement value; pass through `_build_row` with a minimal valid question dict; assert `question["statement"] == statement.strip()`
    - Tag: `Feature: markdown-question-support, Property 7`

- [x] 8. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Plugin order matters: `rehypeHighlight` must run before `rehypeSanitize`; the sanitize schema must allow `class` on `code` and `span` elements
- Property tests use `@fast-check/vitest` (frontend) and `hypothesis` (backend, already in dev dependencies)
- All UI copy and error messages remain in pt-BR per product guidelines
