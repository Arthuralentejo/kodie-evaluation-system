import { ProgressHeader } from "../ui";

export function QuestionsScreen({
  answeredCount,
  currentIndex,
  currentQuestion,
  isBusy,
  missingQuestionIds,
  questions,
  screenError,
  onSaveAnswer,
  onPrev,
  onNext,
  onFinish,
}) {
  const totalQuestions = questions.length;
  const questionNumber = currentIndex + 1;
  const remainingQuestions = Math.max(totalQuestions - answeredCount, 0);
  const progress = totalQuestions > 0 ? Math.round((questionNumber / totalQuestions) * 100) : 0;
  const canFinish = totalQuestions === 20 && answeredCount === totalQuestions;

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
                        disabled={!canFinish}
                        onClick={onFinish}
                        type="button"
                      >
                        Finalizar
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
