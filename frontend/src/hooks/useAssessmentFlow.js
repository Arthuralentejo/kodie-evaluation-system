import { useEffect, useMemo, useRef, useState } from "react";

import { API_BASE, SESSION_KEY, STAGES } from "../config";
import { toApiBirthDate } from "../utils/formatters";
import { readApiError, wait } from "../utils/http";

const QUESTIONS_LIMIT = 20;
const ASSESSMENT_STATUS = {
  IDLE: "IDLE",
  NONE: "NONE",
  DRAFT: "DRAFT",
  COMPLETED: "COMPLETED",
};

function logFlow(event, details = {}, level = "info") {
  const logger = console[level] || console.info;
  logger(`[assessment-flow] ${event}`, details);
}

export function useAssessmentFlow() {
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
  const [assessmentStatus, setAssessmentStatus] = useState(ASSESSMENT_STATUS.IDLE);
  const saveVersionsRef = useRef({});

  const authHeader = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);
  const currentQuestion = questions[currentIndex];
  const answeredCount = questions.filter((question) => Boolean(question.selected_option)).length;
  const completionDate = completedAt ? new Date(completedAt) : new Date();
  const protocolNumber = assessmentId
    ? `KD-${assessmentId.slice(0, 4).toUpperCase()}-${assessmentId.slice(-5)}`
    : "KD-0000-00000";

  useEffect(() => {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (!saved) return;

      const parsed = JSON.parse(saved);
      if (parsed?.token) {
        logFlow("session_restored", { assessmentId: parsed.assessmentId || null });
        setToken(parsed.token);
        if (parsed.assessmentId) {
          setAssessmentId(parsed.assessmentId);
          setStage(STAGES.QUESTIONS);
        } else {
          setStage(STAGES.INTRO);
        }
      }
    } catch (error) {
      logFlow("session_restore_failed", { error: String(error) }, "warn");
      localStorage.removeItem(SESSION_KEY);
    }
  }, []);

  useEffect(() => {
    if (token) {
      const persistedAssessmentId = stage === STAGES.QUESTIONS ? assessmentId : "";
      localStorage.setItem(SESSION_KEY, JSON.stringify({ token, assessmentId: persistedAssessmentId }));
      return;
    }

    localStorage.removeItem(SESSION_KEY);
  }, [token, assessmentId, stage]);

  useEffect(() => {
    if (stage === STAGES.QUESTIONS && token && assessmentId && questions.length === 0) {
      void loadQuestions();
    }
  }, [stage, token, assessmentId, questions.length]);

  useEffect(() => {
    if (stage === STAGES.INTRO && token && !assessmentId) {
      void loadCurrentAssessment();
    }
  }, [stage, token, assessmentId]);

  function resetSession() {
    setToken("");
    setAssessmentId("");
    setQuestions([]);
    setCurrentIndex(0);
    setAnswerStates({});
    setMissingQuestionIds([]);
    setCompletedAt("");
    setAssessmentStatus(ASSESSMENT_STATUS.IDLE);
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
    logFlow("auth_started", { cpfSuffix: cpf.replace(/\D/g, "").slice(-2) });

    try {
      const response = await fetch(`${API_BASE}/auth`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cpf: cpf.replace(/\D/g, ""), birth_date: apiBirthDate }),
      });

      if (!response.ok) {
        const message = await readApiError(response);
        logFlow("auth_failed", { status: response.status, message }, "warn");
        setAuthError(message);
        return;
      }

      const data = await response.json();
      logFlow("auth_succeeded", {});
      setToken(data.token);
      setAssessmentId("");
      setAssessmentStatus(ASSESSMENT_STATUS.IDLE);
      setStage(STAGES.INTRO);
    } catch (error) {
      logFlow("auth_request_failed", { error: String(error) }, "error");
      setAuthError("Nao foi possivel conectar ao servidor.");
    } finally {
      setIsBusy(false);
    }
  }

  async function loadQuestions() {
    setScreenError("");
    setIsBusy(true);
    logFlow("questions_load_started", { assessmentId, quantity: QUESTIONS_LIMIT });

    try {
      const response = await fetch(
        `${API_BASE}/assessments/${assessmentId}/questions?quantity=${QUESTIONS_LIMIT}`,
        { headers: authHeader },
      );

      if (!response.ok) {
        const message = await readApiError(response);
        logFlow("questions_load_failed", { assessmentId, status: response.status, message }, "warn");
        setScreenError(message);
        if (response.status === 401 || response.status === 403) {
          resetSession();
          setStage(STAGES.AUTH);
        }
        return;
      }

      const data = await response.json();
      logFlow("questions_load_succeeded", { assessmentId, count: data.length });
      setQuestions(data);
      setCurrentIndex((previous) => Math.min(previous, Math.max(0, data.length - 1)));
    } catch (error) {
      logFlow("questions_load_request_failed", { assessmentId, error: String(error) }, "error");
      setScreenError("Nao foi possivel carregar as perguntas.");
    } finally {
      setIsBusy(false);
    }
  }

  async function loadCurrentAssessment() {
    setScreenError("");
    setIsBusy(true);
    logFlow("assessment_current_load_started", {});

    try {
      const response = await fetch(`${API_BASE}/assessments/current`, { headers: authHeader });

      if (!response.ok) {
        const message = await readApiError(response);
        logFlow("assessment_current_load_failed", { status: response.status, message }, "warn");
        setScreenError(message);
        if (response.status === 401 || response.status === 403) {
          resetSession();
          setStage(STAGES.AUTH);
        }
        return;
      }

      const data = await response.json();
      logFlow("assessment_current_load_succeeded", { status: data.status, assessmentId: data.assessment_id || null });
      setAssessmentStatus(data.status);
      setCompletedAt(data.completed_at || "");

      if (data.status === ASSESSMENT_STATUS.DRAFT && data.assessment_id) {
        setAssessmentId(data.assessment_id);
        setStage(STAGES.QUESTIONS);
      }
    } catch (error) {
      logFlow("assessment_current_load_request_failed", { error: String(error) }, "error");
      setScreenError("Nao foi possivel verificar sua avaliacao.");
    } finally {
      setIsBusy(false);
    }
  }

  async function startAssessment() {
    if (assessmentStatus === ASSESSMENT_STATUS.COMPLETED) return;

    setScreenError("");
    setIsBusy(true);
    logFlow("assessment_create_started", {});

    try {
      const response = await fetch(`${API_BASE}/assessments`, {
        method: "POST",
        headers: authHeader,
      });

      if (!response.ok) {
        const message = await readApiError(response);
        logFlow("assessment_create_failed", { status: response.status, message }, "warn");
        setScreenError(message);
        if (response.status === 409) {
          await loadCurrentAssessment();
        }
        return;
      }

      const data = await response.json();
      logFlow("assessment_create_succeeded", { assessmentId: data.assessment_id });
      setAssessmentStatus(data.status);
      setAssessmentId(data.assessment_id);
      setStage(STAGES.QUESTIONS);
    } catch (error) {
      logFlow("assessment_create_request_failed", { error: String(error) }, "error");
      setScreenError("Nao foi possivel iniciar a avaliacao.");
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
    logFlow("answer_save_started", { assessmentId, questionId, selectedOption, version: nextVersion });

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
          logFlow("answer_save_succeeded", { assessmentId, questionId, selectedOption, attempt: attempt + 1 });
          setAnswerStates((previous) => ({ ...previous, [questionId]: "saved" }));
          return;
        }
        logFlow(
          "answer_save_retrying",
          { assessmentId, questionId, selectedOption, attempt: attempt + 1, status: response.status },
          "warn",
        );
      } catch (error) {
        logFlow(
          "answer_save_request_failed",
          { assessmentId, questionId, selectedOption, attempt: attempt + 1, error: String(error) },
          "warn",
        );
      }

      await wait(retryWait[attempt]);
    }

    if (saveVersionsRef.current[questionId] === nextVersion) {
      logFlow("answer_save_failed", { assessmentId, questionId, selectedOption, version: nextVersion }, "error");
      setAnswerStates((previous) => ({ ...previous, [questionId]: "error" }));
    }
  }

  async function submitAssessment() {
    setScreenError("");
    setIsSubmitting(true);
    setMissingQuestionIds([]);
    logFlow("submit_started", {
      assessmentId,
      answeredCount,
      loadedQuestionCount: questions.length,
    });

    try {
      const response = await fetch(`${API_BASE}/assessments/${assessmentId}/submit`, {
        method: "POST",
        headers: authHeader,
      });

      if (response.status === 422) {
        const payload = await response.json();
        const missing = payload?.details?.missing_question_ids || payload?.details?.question_ids || [];
        const hiddenMissing = missing.filter((missingId) => !questions.some((question) => question.id === missingId));
        logFlow(
          "submit_incomplete",
          {
            assessmentId,
            requestId: payload?.request_id,
            missingCount: missing.length,
            hiddenMissingCount: hiddenMissing.length,
            hiddenMissing,
          },
          "warn",
        );
        setMissingQuestionIds(missing);
        setScreenError(payload?.message || "Existem perguntas pendentes.");

        if (missing.length > 0) {
          const index = questions.findIndex((question) => question.id === missing[0]);
          if (index >= 0) setCurrentIndex(index);
        }

        setStage(STAGES.QUESTIONS);

        return;
      }

      if (!response.ok) {
        const message = await readApiError(response);
        logFlow("submit_failed", { assessmentId, status: response.status, message }, "error");
        setScreenError(message);
        return;
      }

      const payload = await response.json();
      logFlow("submit_succeeded", { assessmentId, completedAt: payload.completed_at });
      setCompletedAt(payload.completed_at || new Date().toISOString());
      setAssessmentStatus(ASSESSMENT_STATUS.COMPLETED);
      setStage(STAGES.COMPLETED);
    } catch (error) {
      logFlow("submit_request_failed", { assessmentId, error: String(error) }, "error");
      setScreenError("Falha ao enviar a avaliacao.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function resetToStart() {
    resetSession();
    setStage(STAGES.AUTH);
  }

  function logout() {
    resetToStart();
  }

  function goToReview() {
    setScreenError("");
    setStage(STAGES.REVIEW);
  }

  return {
    answeredCount,
    answerStates,
    assessmentId,
    assessmentStatus,
    authError,
    birthDate,
    completedAt,
    completionDate,
    cpf,
    currentIndex,
    currentQuestion,
    isBusy,
    isSubmitting,
    missingQuestionIds,
    protocolNumber,
    questions,
    screenError,
    stage,
    goToReview,
    setBirthDate,
    setCpf,
    setCurrentIndex,
    setStage,
    login,
    loadQuestions,
    logout,
    resetToStart,
    saveAnswer,
    startAssessment,
    submitAssessment,
  };
}
