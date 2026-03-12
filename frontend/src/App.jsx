import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const STEP_COUNT = 5;
const STAGES = {
  AUTH: "AUTH",
  INTRO: "INTRO",
  QUESTIONS: "QUESTIONS",
  COMPLETED: "COMPLETED",
};

const SESSION_KEY = "kodie.session";

function maskCpf(value) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  const parts = [
    digits.slice(0, 3),
    digits.slice(3, 6),
    digits.slice(6, 9),
    digits.slice(9, 11),
  ];

  return [parts[0], parts[1], parts[2]].filter(Boolean).join(".") + (parts[3] ? `-${parts[3]}` : "");
}

function normalizeDateInput(value) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

function toApiBirthDate(displayDate) {
  const match = displayDate.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!match) return "";
  const [, dd, mm, yyyy] = match;
  return `${yyyy}-${mm}-${dd}`;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readApiError(res) {
  let message = "Nao foi possivel concluir a operacao.";

  try {
    const payload = await res.json();
    message = payload?.message || payload?.code || message;
  } catch {
    message = `${message} (HTTP ${res.status})`;
  }

  return message;
}

function BrandMark() {
  return (
    <div className="brand-mark">
      <span className="brand-mark__icon" />
      <span>Kodie</span>
    </div>
  );
}

function StepHeader({ step, title }) {
  const progress = Math.round((step / STEP_COUNT) * 100);

  return (
    <header className="progress-header">
      <div className="progress-header__row">
        <div className="progress-header__left">
          <BrandMark />
          <span className="progress-header__step">
            Etapa {step} de {STEP_COUNT} · {title}
          </span>
        </div>
        <strong className="progress-header__percent">{progress}% concluido</strong>
      </div>
      <div className="progress-header__track" aria-hidden="true">
        <div className="progress-header__fill" style={{ width: `${progress}%` }} />
      </div>
    </header>
  );
}

function HelpLink() {
  return (
    <button className="text-help" type="button">
      <span className="text-help__icon">?</span>
      Precisa de ajuda?
    </button>
  );
}

function InfoCard({ icon, title, children }) {
  return (
    <article className="info-card">
      <div className="info-card__icon" aria-hidden="true">
        {icon}
      </div>
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
    </article>
  );
}

function Badge({ children }) {
  return <span className="pill-badge">{children}</span>;
}

function AuthPanel({
  cpf,
  birthDate,
  authError,
  isBusy,
  onCpfChange,
  onBirthDateChange,
  onSubmit,
}) {
  return (
    <div className="panel panel--form">
      <div className="panel__content">
        <h2>Informe seus dados</h2>
        <p>Preencha os campos abaixo para continuar para a proxima etapa.</p>

        <form className="form-stack" onSubmit={onSubmit}>
          <label htmlFor="cpf">CPF</label>
          <div className="field">
            <input
              id="cpf"
              value={cpf}
              onChange={(event) => onCpfChange(maskCpf(event.target.value))}
              inputMode="numeric"
              autoComplete="off"
              placeholder="000.000.000-00"
              required
            />
            <span className="field__icon" aria-hidden="true">
              U
            </span>
          </div>
          <small>Digite apenas numeros.</small>

          <label htmlFor="birth_date">Data de nascimento</label>
          <div className="field">
            <input
              id="birth_date"
              value={birthDate}
              onChange={(event) => onBirthDateChange(normalizeDateInput(event.target.value))}
              inputMode="numeric"
              autoComplete="bday"
              placeholder="DD/MM/AAAA"
              required
            />
            <span className="field__icon" aria-hidden="true">
              C
            </span>
          </div>
          <small>Use o formato com dia, mes e ano.</small>

          {authError && <p className="feedback feedback--error">{authError}</p>}

          <button className="button button--primary button--wide" disabled={isBusy} type="submit">
            {isBusy ? "Validando..." : "Continuar"}
          </button>
        </form>

        <HelpLink />
      </div>
    </div>
  );
}

function IntroPanel({ onStart, onBack, isBusy }) {
  return (
    <div className="panel panel--side">
      <div className="panel__content panel__content--side">
        <h2>Recomendacoes rapidas</h2>
        <p>Organize seu ambiente antes de iniciar para manter o foco durante toda a etapa.</p>

        <div className="highlight-box">
          <div className="highlight-box__icon" aria-hidden="true">
            *
          </div>
          <div>
            <h3>Dica pratica</h3>
            <p>Procure um local silencioso, mantenha uma leitura continua e avance no seu ritmo.</p>
          </div>
        </div>

        <div className="tag-row">
          <Badge>Layout preparado para leitura em desktop</Badge>
          <Badge>Etapa curta e objetiva</Badge>
        </div>

        <div className="action-row">
          <button className="button button--primary" onClick={onStart} disabled={isBusy} type="button">
            Iniciar avaliacao
          </button>
          <button className="button button--secondary" onClick={onBack} type="button">
            Voltar
          </button>
        </div>
      </div>
    </div>
  );
}

export function App() {
  const [stage, setStage] = useState(STAGES.AUTH);
  const [cpf, setCpf] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [token, setToken] = useState("");
  const [assessmentId, setAssessmentId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answerStates, setAnswerStates] = useState({});
  const [missingQuestionIds, setMissingQuestionIds] = useState([]);
  const [authError, setAuthError] = useState("");
  const [screenError, setScreenError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [completedAt, setCompletedAt] = useState("");
  const saveVersionsRef = useRef({});

  const authHeader = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);
  const currentQuestion = questions[currentIndex];
  const answeredCount = questions.filter((question) => Boolean(question.selected_option)).length;
  const completionDate = completedAt ? new Date(completedAt) : new Date();
  const protocolNumber = assessmentId ? `KD-${assessmentId.slice(0, 4).toUpperCase()}-${assessmentId.slice(-5)}` : "KD-0000-00000";

  useEffect(() => {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (!saved) return;
      const parsed = JSON.parse(saved);
      if (parsed?.token && parsed?.assessmentId) {
        setToken(parsed.token);
        setAssessmentId(parsed.assessmentId);
        setStage(STAGES.QUESTIONS);
      }
    } catch {
      localStorage.removeItem(SESSION_KEY);
    }
  }, []);

  useEffect(() => {
    if (token && assessmentId) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({ token, assessmentId }));
      return;
    }

    localStorage.removeItem(SESSION_KEY);
  }, [token, assessmentId]);

  useEffect(() => {
    if (stage === STAGES.QUESTIONS && token && assessmentId && questions.length === 0) {
      void loadQuestions();
    }
  }, [stage, token, assessmentId, questions.length]);

  function resetSession() {
    setToken("");
    setAssessmentId("");
    setQuestions([]);
    setCurrentIndex(0);
    setAnswerStates({});
    setMissingQuestionIds([]);
    setCompletedAt("");
    setScreenError("");
    localStorage.removeItem(SESSION_KEY);
  }

  async function login(event) {
    event.preventDefault();
    setAuthError("");
    setScreenError("");

    const apiBirthDate = toApiBirthDate(birthDate);
    if (cpf.replace(/\D/g, "").length !== 11 || !apiBirthDate) {
      setAuthError("Informe um CPF e uma data de nascimento validos.");
      return;
    }

    setIsBusy(true);

    try {
      const response = await fetch(`${API_BASE}/auth`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cpf: cpf.replace(/\D/g, ""), birth_date: apiBirthDate }),
      });

      if (!response.ok) {
        setAuthError(await readApiError(response));
        return;
      }

      const data = await response.json();
      setToken(data.token);
      setAssessmentId(data.assessment_id);
      setStage(STAGES.INTRO);
    } catch {
      setAuthError("Nao foi possivel conectar ao servidor.");
    } finally {
      setIsBusy(false);
    }
  }

  async function loadQuestions() {
    setScreenError("");
    setIsBusy(true);

    try {
      const response = await fetch(`${API_BASE}/assessments/${assessmentId}/questions`, { headers: authHeader });

      if (!response.ok) {
        setScreenError(await readApiError(response));
        if (response.status === 401 || response.status === 403) {
          resetSession();
          setStage(STAGES.AUTH);
        }
        return;
      }

      const data = await response.json();
      setQuestions(data);
      setCurrentIndex((previous) => Math.min(previous, Math.max(0, data.length - 1)));
    } catch {
      setScreenError("Nao foi possivel carregar as perguntas.");
    } finally {
      setIsBusy(false);
    }
  }

  async function saveAnswer(questionId, selectedOption) {
    setMissingQuestionIds((previous) => previous.filter((id) => id !== questionId));
    setQuestions((current) =>
      current.map((question) => (
        question.id === questionId ? { ...question, selected_option: selectedOption } : question
      ))
    );

    const nextVersion = (saveVersionsRef.current[questionId] || 0) + 1;
    saveVersionsRef.current[questionId] = nextVersion;
    setAnswerStates((previous) => ({ ...previous, [questionId]: "saving" }));

    const retryWait = [300, 800, 1500];

    for (let attempt = 0; attempt < retryWait.length; attempt += 1) {
      try {
        const response = await fetch(`${API_BASE}/assessments/${assessmentId}/answers`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", ...authHeader },
          body: JSON.stringify({ question_id: questionId, selected_option: selectedOption }),
        });

        if (saveVersionsRef.current[questionId] !== nextVersion) return;

        if (response.ok) {
          setAnswerStates((previous) => ({ ...previous, [questionId]: "saved" }));
          return;
        }
      } catch {
        // Retry handled below.
      }

      await wait(retryWait[attempt]);
    }

    if (saveVersionsRef.current[questionId] === nextVersion) {
      setAnswerStates((previous) => ({ ...previous, [questionId]: "error" }));
    }
  }

  async function submitAssessment() {
    setScreenError("");
    setIsSubmitting(true);
    setMissingQuestionIds([]);

    try {
      const response = await fetch(`${API_BASE}/assessments/${assessmentId}/submit`, {
        method: "POST",
        headers: authHeader,
      });

      if (response.status === 422) {
        const payload = await response.json();
        const missing = payload?.details?.question_ids || [];
        setMissingQuestionIds(missing);
        setScreenError(payload?.message || "Existem perguntas pendentes.");

        if (missing.length > 0) {
          const index = questions.findIndex((question) => question.id === missing[0]);
          if (index >= 0) setCurrentIndex(index);
        }

        return;
      }

      if (!response.ok) {
        setScreenError(await readApiError(response));
        return;
      }

      const payload = await response.json();
      setCompletedAt(payload.completed_at || new Date().toISOString());
      setStage(STAGES.COMPLETED);
    } catch {
      setScreenError("Falha ao enviar a avaliacao.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="app-shell">
      {stage === STAGES.AUTH && (
        <section className="stage-screen">
          <StepHeader step={1} title="Identificacao" />
          <div className="desktop-grid">
            <div className="panel panel--content">
              <div className="panel__content">
                <p className="eyebrow">Plataforma de avaliacao</p>
                <h1>Vamos comecar com sua identificacao</h1>
                <p className="lead">
                  Use seus dados para acessar a jornada de avaliacao com seguranca. O processo e simples,
                  direto e leva apenas alguns minutos.
                </p>

                <div className="info-stack">
                  <InfoCard icon="S" title="Acesso seguro">
                    Seus dados sao usados apenas para identificar sua sessao nesta etapa.
                  </InfoCard>
                  <InfoCard icon="O" title="Jornada em etapas">
                    A barra no topo mostra exatamente onde voce esta e quanto falta concluir.
                  </InfoCard>
                  <InfoCard icon="C" title="Orientacao clara">
                    Voce vera instrucoes curtas e acoes objetivas em todas as telas.
                  </InfoCard>
                </div>

                <div className="tag-row">
                  <Badge>Sessao protegida</Badge>
                  <Badge>Leitura rapida e objetiva</Badge>
                </div>
              </div>
            </div>

            <AuthPanel
              cpf={cpf}
              birthDate={birthDate}
              authError={authError}
              isBusy={isBusy}
              onCpfChange={setCpf}
              onBirthDateChange={setBirthDate}
              onSubmit={login}
            />
          </div>
        </section>
      )}

      {stage === STAGES.INTRO && (
        <section className="stage-screen">
          <StepHeader step={2} title="Introducao" />
          <div className="desktop-grid">
            <div className="panel panel--content">
              <div className="panel__content">
                <p className="eyebrow">Antes da primeira questao</p>
                <h1>Veja como a avaliacao vai funcionar</h1>
                <p className="lead">
                  Esta etapa prepara voce para responder com tranquilidade. Leia as orientacoes abaixo e
                  inicie quando estiver pronto.
                </p>

                <div className="info-stack">
                  <InfoCard icon="T" title="Reserve alguns minutos">
                    A jornada foi pensada para ser objetiva e pode ser concluida com leitura calma e continua.
                  </InfoCard>
                  <InfoCard icon="V" title="Responda com sinceridade">
                    Nao existe resposta certa ou errada. O mais importante e responder de acordo com sua percepcao.
                  </InfoCard>
                  <InfoCard icon="?" title="Se precisar, voce pode pular">
                    Caso nao saiba responder uma pergunta no momento, siga em frente e revise depois.
                  </InfoCard>
                </div>
              </div>
            </div>

            <IntroPanel onStart={() => setStage(STAGES.QUESTIONS)} onBack={() => setStage(STAGES.AUTH)} isBusy={isBusy} />
          </div>
        </section>
      )}

      {stage === STAGES.QUESTIONS && (
        <section className="stage-screen">
          <StepHeader step={3} title="Questionario" />
          <div className="desktop-grid desktop-grid--questionnaire">
            <aside className="panel panel--side panel--sticky">
              <div className="panel__content panel__content--side">
                <h2>Progresso da etapa</h2>
                <p>
                  {answeredCount} de {questions.length} respondidas
                </p>

                <div className="question-list">
                  {questions.map((question, index) => {
                    const state =
                      currentIndex === index
                        ? "current"
                        : question.selected_option
                          ? "answered"
                          : missingQuestionIds.includes(question.id)
                            ? "missing"
                            : "";

                    return (
                      <button
                        className={`question-list__item ${state}`}
                        key={question.id}
                        onClick={() => setCurrentIndex(index)}
                        type="button"
                      >
                        <span>Questao {index + 1}</span>
                        <strong>{question.selected_option ? "Respondida" : "Pendente"}</strong>
                      </button>
                    );
                  })}
                </div>
              </div>
            </aside>

            <div className="panel panel--content">
              <div className="panel__content">
                {screenError && <p className="feedback feedback--error">{screenError}</p>}

                {!currentQuestion && (
                  <div className="empty-state">
                    <h2>{isBusy ? "Carregando perguntas..." : "Nenhuma pergunta disponivel."}</h2>
                  </div>
                )}

                {currentQuestion && (
                  <>
                    <p className="eyebrow">
                      Questao {currentIndex + 1} de {questions.length}
                    </p>
                    <h1>{currentQuestion.statement}</h1>

                    <div className="options-stack">
                      {currentQuestion.options.map((option) => {
                        const isSelected = currentQuestion.selected_option === option.key;

                        return (
                          <button
                            className={`option-card ${isSelected ? "selected" : ""}`}
                            key={option.key}
                            onClick={() => saveAnswer(currentQuestion.id, option.key)}
                            type="button"
                          >
                            <span className="option-card__key">{option.key}</span>
                            <span className="option-card__text">{option.text}</span>
                          </button>
                        );
                      })}
                    </div>

                    <button
                      className={`text-button ${currentQuestion.selected_option === "DONT_KNOW" ? "active" : ""}`}
                      onClick={() => saveAnswer(currentQuestion.id, "DONT_KNOW")}
                      type="button"
                    >
                      Nao sei responder
                    </button>

                    <p className={`feedback feedback--status ${answerStates[currentQuestion.id] || ""}`}>
                      {answerStates[currentQuestion.id] === "saving" && "Salvando resposta..."}
                      {answerStates[currentQuestion.id] === "saved" && "Resposta salva com sucesso."}
                      {answerStates[currentQuestion.id] === "error" && "Falha ao salvar. Tente novamente."}
                    </p>

                    <div className="action-row action-row--questionnaire">
                      <button
                        className="button button--secondary"
                        disabled={currentIndex === 0}
                        onClick={() => setCurrentIndex((value) => Math.max(0, value - 1))}
                        type="button"
                      >
                        Anterior
                      </button>

                      {currentIndex < questions.length - 1 ? (
                        <button
                          className="button button--primary"
                          disabled={questions.length === 0}
                          onClick={() => setCurrentIndex((value) => Math.min(questions.length - 1, value + 1))}
                          type="button"
                        >
                          Proxima
                        </button>
                      ) : (
                        <button
                          className="button button--primary"
                          disabled={isSubmitting || questions.length === 0}
                          onClick={submitAssessment}
                          type="button"
                        >
                          {isSubmitting ? "Enviando..." : "Finalizar"}
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {stage === STAGES.COMPLETED && (
        <section className="stage-screen">
          <StepHeader step={5} title="Conclusao" />
          <div className="completion-layout">
            <div className="panel panel--completion">
              <div className="panel__content panel__content--completion">
                <div className="success-mark" aria-hidden="true">
                  V
                </div>
                <h1>Avaliacao concluida com sucesso</h1>
                <p className="lead">
                  Recebemos suas respostas. Voce pode encerrar esta sessao com tranquilidade. Se necessario,
                  guarde os dados de referencia abaixo.
                </p>

                <div className="session-card">
                  <h2>Dados da sessao</h2>
                  <div className="session-grid">
                    <div>
                      <span>Numero de protocolo</span>
                      <strong>{protocolNumber}</strong>
                    </div>
                    <div>
                      <span>Data</span>
                      <strong>{completionDate.toLocaleDateString("pt-BR")}</strong>
                    </div>
                    <div>
                      <span>Etapas concluidas</span>
                      <strong>5 de 5</strong>
                    </div>
                    <div>
                      <span>Status</span>
                      <strong>Envio confirmado</strong>
                    </div>
                  </div>
                </div>

                <div className="action-row">
                  <button
                    className="button button--primary"
                    onClick={() => {
                      resetSession();
                      setStage(STAGES.AUTH);
                    }}
                    type="button"
                  >
                    Encerrar
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
