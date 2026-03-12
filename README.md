# Kodie — Sistema de Avaliação

Plataforma web *mobile-first* para avaliação de nível de conhecimento em tecnologia dos participantes da Kodie. Substitui processos manuais por um fluxo estruturado de coleta de respostas, gerando dados padronizados para análise e classificação de participantes por trilha de desenvolvimento.

---

## Arquitetura

### Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React |
| Backend / API | Python — FastAPI |
| Banco de Dados | MongoDB (com schema definition via Pydantic) |
| Infraestrutura | MongoDB Atlas + Render |
| Extração de Dados | Python script (ETL) |

### Modelagem de Dados

MongoDB com schema definition explícito via modelos Pydantic. Apesar da flexibilidade do documento, os schemas são definidos e validados na camada da aplicação para garantir integridade dos dados para extração.

```python
# Estrutura dos documentos

Student:
  cpf: str (unique)
  birth_date: date
  name: str
  created_at: datetime

Question:
  statement: str
  options: list[{ key: str, text: str }]
  correct_option: str
  category: str

Assessment:
  student_id: ObjectId  # ref: Student
  status: Literal["DRAFT", "COMPLETED"]
  started_at: datetime
  completed_at: datetime | None

Answer:
  assessment_id: ObjectId  # ref: Assessment
  question_id: ObjectId    # ref: Question
  selected_option: str     # key da alternativa ou "DONT_KNOW"
  answered_at: datetime
```

> Respostas armazenadas em documento próprio (`Answer`) para viabilizar análises granulares — ex: taxa de erro por questão, distribuição de respostas por categoria.

---

## Fluxo da Aplicação

### Autenticação
- Identificação via **CPF + Data de Nascimento**. Sem criação de senha.
- Participantes são pré-cadastrados via importação da base de dados da Kodie.
- Autenticação retorna um token de sessão para as requisições subsequentes.

### Auto-Save
- A cada resposta selecionada, o cliente envia uma requisição assíncrona (`PATCH /assessments/:id/answers`) salvando o estado no banco.
- Garante resiliência em cenários de conexão intermitente — o participante retoma de onde parou.

### Embaralhamento de Alternativas
- A API embaralha a ordem das alternativas antes de enviar as questões ao cliente, evitando decoreba entre participantes.

### Submissão
- Ao concluir, o cliente envia `POST /assessments/:id/submit`.
- O backend altera o status do assessment para `COMPLETED` e registra o `completed_at`.

---

## Endpoints da API

```
POST   /auth                          Autenticação do participante
GET    /assessments/:id/questions     Retorna questões embaralhadas
PATCH  /assessments/:id/answers       Auto-save de resposta individual
POST   /assessments/:id/submit        Finalização da avaliação
```

---

## Extração de Dados (v1)

Nesta versão, **não há dashboard ou exportação automatizada**. A extração é executada por um script Python dedicado que consulta o MongoDB Atlas, cruza as coleções (`assessments`, `answers`, `questions`, `students`) e gera um dataset estruturado em CSV pronto para análise.

```
scripts/
  extract.py   Conecta ao Atlas, agrega os dados e exporta o dataset
```

O dataset gerado consolida, por participante:
- Respostas selecionadas por questão
- Acertos e erros por categoria
- Status de conclusão e tempo de avaliação

As análises de inteligência — classificação por nível, identificação de lacunas por tema e geração de relatórios — são conduzidas pelo time da Kodie sobre esse dataset.

A automação desse processo é candidata para versões subsequentes.

---

## Monorepo (v1 em implementação)

```
backend/   FastAPI + Motor + JWT + testes
frontend/  React + Vite (fluxo mobile-first)
scripts/   ETL (pymongo + pandas)
infra/     Configuração de deploy (Render) e envs
```

### Dependências e pinos

- Backend async I/O: `motor>=3.7,<4`
- ETL batch jobs: `pymongo>=4.12,<5`
- API framework: `fastapi>=0.116,<1`
- ETL dataframe: `pandas>=2.2,<3`

### Execução local rápida

Backend:
```
cd backend
pip install -e .[dev]
uvicorn app.main:app --reload
```

Frontend:
```
cd frontend
npm install
npm run dev
```

---

## Infraestrutura

| Serviço | Plataforma |
|---|---|
| Banco de Dados | MongoDB Atlas (cluster compartilhado na v1) |
| Backend (API) | Render — Web Service (Python) |
| Frontend | Render — Static Site (React) |

O Render realiza deploy automático a partir de pushes na branch principal do repositório.

---

## Roadmap

**v1 — Escopo atual**
- [ ] Modelagem dos schemas e configuração do MongoDB Atlas
- [ ] Script de importação da base de participantes (CSV → Atlas)
- [ ] API FastAPI: autenticação, auto-save e submissão
- [ ] Frontend React: identificação, briefing, questionário e encerramento
- [ ] Script de extração (`extract.py`) gerando dataset CSV
- [ ] Deploy no Render (backend + frontend)

**v2 — Pós-validação**
- [ ] Automação da extração e geração periódica do dataset
- [ ] Dashboard analítico para o time da Kodie
- [ ] Testes de carga (cenário de múltiplos acessos simultâneos)
