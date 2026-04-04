# Product

Kodie is a web-based technology knowledge assessment platform. Students authenticate with CPF + birth date, then complete a fixed-set multiple-choice exam. The system tracks progress, persists answers in real time, and produces a completion protocol on submission.

## Core Rules

- Authentication is CPF + birth date only (no passwords)
- A student may have at most one DRAFT assessment at a time
- A student who has completed an assessment cannot start a new one
- The question set is frozen at draft creation (`assigned_question_ids`)
- Answer option order is deterministically shuffled per assessment + question
- Answers are embedded in the assessment document (no separate answers collection)
- `DONT_KNOW` is a valid answer option for any question

## Assessment Lifecycle

`DRAFT` → (all questions answered) → `COMPLETED`

## User-Facing Language

The product UI is in Brazilian Portuguese. Error messages, labels, and content strings should be in pt-BR.
