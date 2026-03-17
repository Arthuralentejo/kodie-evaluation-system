import { useEffect, useMemo, useRef, useState } from "react";

import { API_BASE, SESSION_KEY, STAGES } from "../config";
import { toApiBirthDate } from "../utils/formatters";
import { readApiError, wait } from "../utils/http";

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

  function resetToStart() {
    resetSession();
    setStage(STAGES.AUTH);
  }

  return {
    answeredCount,
    answerStates,
    assessmentId,
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
    setBirthDate,
    setCpf,
    setCurrentIndex,
    setStage,
    login,
    loadQuestions,
    resetToStart,
    saveAnswer,
    submitAssessment,
  };
}
