# Requirements Document

## Introduction

The Kodie assessment platform currently renders question text as plain text. Several questions (particularly at the pleno/senior levels) contain markdown-formatted content — including fenced code blocks in Python, JavaScript, SQL, Bash, Dockerfile, and YAML — that must be rendered with proper formatting and syntax highlighting so students can read and understand the code clearly.

This feature adds markdown rendering support to the `QuestionsScreen` component and ensures the source exam data (`assets/exam.md` and `backend/scripts/exam.jsonl`) is consistently formatted with valid markdown.

## Glossary

- **QuestionsScreen**: The React component that displays the current question and answer options to the student during an assessment.
- **Markdown_Renderer**: The frontend component responsible for parsing and rendering markdown-formatted text as React components, using `react-markdown` with rehype plugins.
- **Question_Statement**: The `statement` field of a question document, which may contain plain text or markdown-formatted content including fenced code blocks.
- **Fenced_Code_Block**: A markdown construct delimited by triple backticks (` ``` `) with an optional language identifier (e.g., ` ```python `).
- **Syntax_Highlighting**: Visual differentiation of code tokens (keywords, strings, comments, etc.) by color or weight.
- **rehype-highlight**: A rehype plugin that applies syntax highlighting to fenced code blocks using `highlight.js` class-based markup.
- **rehype-sanitize**: A rehype plugin that sanitizes the rendered HTML output to prevent XSS attacks by stripping disallowed tags and attributes.
- **exam.jsonl**: The JSONL seed file at `backend/scripts/exam.jsonl` used to populate the questions collection in MongoDB.
- **exam.md**: The human-readable source exam file at `assets/exam.md`.

## Requirements

### Requirement 1: Render Markdown in Question Statements

**User Story:** As a student, I want question text that contains code snippets to be displayed with proper code formatting, so that I can read and understand the code clearly during the assessment.

#### Acceptance Criteria

1. WHEN a `Question_Statement` contains a `Fenced_Code_Block`, THE `Markdown_Renderer` SHALL render it as a styled `<pre><code>` block with monospace font and preserved whitespace.
2. WHEN a `Question_Statement` contains inline code (single backtick), THE `Markdown_Renderer` SHALL render it as a styled `<code>` element distinct from surrounding prose.
3. WHEN a `Question_Statement` contains only plain text with no markdown syntax, THE `Markdown_Renderer` SHALL render it as plain paragraph text with no visible change in appearance.
4. THE `Markdown_Renderer` SHALL use `react-markdown` to parse and render markdown content as React components.
5. THE `Markdown_Renderer` SHALL use `rehype-sanitize` as a rehype plugin to sanitize rendered HTML output and prevent XSS injection.
6. THE `Markdown_Renderer` SHALL support at minimum the following fenced code block languages: `python`, `javascript`, `sql`, `bash`, `dockerfile`, `yaml`.

### Requirement 2: Syntax Highlighting for Code Blocks

**User Story:** As a student, I want code blocks in questions to have syntax highlighting, so that I can distinguish keywords, strings, and other code elements at a glance.

#### Acceptance Criteria

1. WHEN a `Fenced_Code_Block` specifies a supported language identifier, THE `Markdown_Renderer` SHALL apply syntax highlighting appropriate to that language using `rehype-highlight`.
2. WHEN a `Fenced_Code_Block` has no language identifier or an unrecognized language identifier, THE `Markdown_Renderer` SHALL render the block with code formatting but without syntax highlighting, and SHALL NOT throw an error.
3. THE `Markdown_Renderer` SHALL apply a color scheme for syntax highlighting that maintains a contrast ratio of at least 4.5:1 against the code block background, in accordance with WCAG 2.1 AA guidelines.

### Requirement 3: Visual Integration with Existing UI

**User Story:** As a student, I want the rendered markdown to look consistent with the rest of the assessment UI, so that the experience feels cohesive and professional.

#### Acceptance Criteria

1. THE `Markdown_Renderer` SHALL render code blocks using a background color and border visually distinct from the `question-heading-card` panel background.
2. THE `Markdown_Renderer` SHALL render code blocks with horizontal scrolling when the code content exceeds the container width, rather than wrapping lines.
3. THE `Markdown_Renderer` SHALL apply styles exclusively via `styles.css` class selectors, without introducing inline styles or a CSS-in-JS solution.
4. WHEN rendered on a viewport narrower than 768px, THE `Markdown_Renderer` SHALL maintain readable code block formatting with appropriate font size and scroll behavior.

### Requirement 4: Consistent Exam Data Formatting

**User Story:** As a content author, I want the exam source files to use consistent and valid markdown formatting, so that all code-bearing questions render correctly after the markdown renderer is introduced.

#### Acceptance Criteria

1. THE `exam.jsonl` file SHALL use valid fenced code block syntax (triple backticks with a language identifier) for all questions that contain code snippets.
2. THE `exam.md` file SHALL use valid fenced code block syntax for all questions that contain code snippets, consistent with `exam.jsonl`.
3. WHEN `seed_questions.py` seeds `exam.jsonl` into MongoDB, THE seeding script SHALL preserve the markdown content of `Question_Statement` fields without modification or escaping.
