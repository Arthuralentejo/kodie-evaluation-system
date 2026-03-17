import { ProgressHeader } from "../ui";

export function QuestionsScreen({
  answeredCount,
  currentIndex,
  currentQuestion,
  isBusy,
  isSubmitting,
  missingQuestionIds,
  questions,
  screenError,
  answerStates,
  onSelectQuestion,
  onSaveAnswer,
  onPrev,
  onNext,
  onSubmit,
}) {
  const totalQuestions = questions.length;
  const questionNumber = currentIndex + 1;
  const remainingQuestions = Math.max(totalQuestions - answeredCount, 0);
  const progress = totalQuestions > 0 ? Math.round((questionNumber / totalQuestions) * 100) : 0;

  return (
    <section className="stage-screen">
      <ProgressHeader
        leftText={`Questao ${questionNumber} de ${totalQuestions || 0}`}
        rightText={`${remainingQuestions} questoes restantes`}
        progress={progress}
      />
      <div className="question-layout">
        <div className="question-main">
          <div className="panel panel--content panel--question">
            <div className="panel__content panel__content--question">
              {screenError && <p className="feedback feedback--error">{screenError}</p>}

              {!currentQuestion && (
                <div className="empty-state">
                  <h2>{isBusy ? "Carregando perguntas..." : "Nenhuma pergunta disponivel."}</h2>
                </div>
              )}

              {currentQuestion && (
                <>
                  <div className="question-heading-card">
                    <h1>{currentQuestion.statement}</h1>
                  </div>

                  <div className="options-stack options-stack--spacious">
                    {currentQuestion.options.map((option) => {
                      const isSelected = currentQuestion.selected_option === option.key;
                      const isMissing =
                        missingQuestionIds.includes(currentQuestion.id) && !currentQuestion.selected_option;

                      return (
                        <button
                          className={`option-card option-card--large ${isSelected ? "selected" : ""} ${isMissing ? "missing" : ""}`}
                          key={option.key}
                          onClick={() => onSaveAnswer(currentQuestion.id, option.key)}
                          type="button"
                        >
                          <span className="option-card__key option-card__key--large">{option.key}</span>
                          <span className="option-card__text option-card__text--large">{option.text}</span>
                        </button>
                      );
                    })}
                  </div>

                  <p className={`feedback feedback--status ${answerStates[currentQuestion.id] || ""}`}>
                    {answerStates[currentQuestion.id] === "saving" && "Salvando resposta..."}
                    {answerStates[currentQuestion.id] === "saved" && "Resposta salva com sucesso."}
                    {answerStates[currentQuestion.id] === "error" && "Falha ao salvar. Tente novamente."}
                  </p>

                  <div className="question-footer">
                    <button
                      className="button button--secondary button--compact"
                      disabled={currentIndex === 0}
                      onClick={onPrev}
                      type="button"
                    >
                      Anterior
                    </button>

                    <button
                      className={`text-button text-button--muted ${currentQuestion.selected_option === "DONT_KNOW" ? "active" : ""}`}
                      onClick={() => onSaveAnswer(currentQuestion.id, "DONT_KNOW")}
                      type="button"
                    >
                      Nao sei responder
                    </button>

                    {currentIndex < questions.length - 1 ? (
                      <button
                        className="button button--primary button--compact"
                        disabled={questions.length === 0}
                        onClick={onNext}
                        type="button"
                      >
                        Proxima
                      </button>
                    ) : (
                      <button
                        className="button button--primary button--compact"
                        disabled={isSubmitting || questions.length === 0}
                        onClick={onSubmit}
                        type="button"
                      >
                        {isSubmitting ? "Enviando..." : "Proxima"}
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
          {totalQuestions > 0 ? (
            <div className="question-jump-list" aria-label="Selecionar questao">
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
                    className={`question-jump ${state}`}
                    key={question.id}
                    onClick={() => onSelectQuestion(index)}
                    type="button"
                  >
                    {index + 1}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
