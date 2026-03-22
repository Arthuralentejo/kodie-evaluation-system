# Kodie - Sistema de Avaliacao

Plataforma web para avaliacao de conhecimento em tecnologia.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React |
| Backend | FastAPI |
| Banco | MongoDB |
| Infra | MongoDB Atlas + Render |

## Modelo de Dados Atual

### students

```text
_id: ObjectId
cpf: string (unico, normalizado)
birth_date: datetime
name: string
created_at: datetime
```

### questions

```text
_id: ObjectId
number: int (unico)
statement: string
options: [{ key, text }]
correct_option: string
category: "iniciante" | "junior" | "pleno" | "senior"
```

### assessments

```text
_id: ObjectId
student_id: ObjectId
assigned_question_ids: ObjectId[]
answers: [{ question_id, selected_option, answered_at }]
status: "DRAFT" | "COMPLETED"
started_at: datetime
completed_at: datetime | null
```

### token_denylist

```text
_id: ObjectId
jti: string
expires_at: datetime
revoked_at: datetime
```

### auth_attempts

```text
_id: ObjectId
kind: "cpf" | "ip"
key: string
count: int
window_start: datetime
lock_until: datetime | null
updated_at: datetime
```

## Regras Principais

- autenticacao por CPF + data de nascimento
- um aluno pode ter no maximo um assessment `DRAFT`
- o conjunto de questoes do assessment e congelado em `assigned_question_ids` no bootstrap do draft
- as respostas ficam embutidas no proprio assessment
- a ordem das alternativas e embaralhada de forma deterministica por `assessment_id` + `question_id`

## Endpoints

```text
GET    /live
GET    /ready
POST   /auth
POST   /auth/revoke
GET    /assessments/:id/questions?quantity=N
PATCH  /assessments/:id/answers
POST   /assessments/:id/submit
```

## Arquitetura do Backend

- routers usam dependencies para recuperar services do `request.state`
- services concentram regras de negocio
- repositories concentram operacoes de storage
- o wiring acontece no lifespan do FastAPI

## Estrutura

```text
backend/   API FastAPI, repositories, services e testes
frontend/  Aplicacao React
docs/      Documentacao tecnica
infra/     Configuracoes de deploy
```
