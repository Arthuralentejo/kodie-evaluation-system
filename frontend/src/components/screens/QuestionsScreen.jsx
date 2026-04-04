import { BrandMark } from "../ui";

function QuestionsHeader({ currentIndex, onJumpToQuestion, onLogout, questions, remainingQuestions }) {
  return (
    <header className="questionnaire-header">
      <div className="questionnaire-header__brand">
        <BrandMark />
      </div>
      <div className="questionnaire-header__stepper" aria-label="Navegacao entre perguntas">
        {questions.map((question, index) => {
          const statusClassName =
            index === currentIndex
              ? "is-active"
              : question.selected_option
                ? "is-answered"
                : "is-idle";

          return (
            <button
              className={`questionnaire-step ${statusClassName}`}
              key={question.id}
              onClick={() => onJumpToQuestion(index)}
              type="button"
            >
              {index + 1}
            </button>
          );
        })}
      </div>
      <div className="questionnaire-header__meta">
        <strong className="questionnaire-header__summary">
          {`Questao ${currentIndex + 1} de ${questions.length || 0} · ${remainingQuestions} restantes`}
        </strong>
        <button className="header-action" onClick={onLogout} type="button">
          Sair
        </button>
      </div>
    </header>
  );
}

export function QuestionsScreen({
  answeredCount,
  currentIndex,
  currentQuestion,
  isBusy,
  missingQuestionIds,
  questions,
  screenError,
  onLogout,
  onSaveAnswer,
  onJumpToQuestion,
  onPrev,
  onNext,
  onFinish,
}) {
  const totalQuestions = questions.length;
  const questionNumber = totalQuestions > 0 ? currentIndex + 1 : 0;
  const remainingQuestions = Math.max(totalQuestions - answeredCount, 0);
  const canFinish = totalQuestions > 0 && answeredCount === totalQuestions;
  const options = currentQuestion
    ? [
        ...currentQuestion.options,
        { key: "DONT_KNOW", text: "Nao sei responder.", isUtilityOption: true },
      ]
    : [];

  return (
    <section className="stage-screen">
      <QuestionsHeader
        currentIndex={currentIndex}
        onJumpToQuestion={onJumpToQuestion}
        onLogout={onLogout}
        questions={questions}
        remainingQuestions={remainingQuestions}
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
                  <p className="question-caption">
                    Selecione a alternativa que melhor representa sua percepcao neste momento.
                  </p>

                  <div className="options-stack options-stack--spacious">
                    {options.map((option) => {
                      const isSelected = currentQuestion.selected_option === option.key;
                      const isMissing =
                        missingQuestionIds.includes(currentQuestion.id) && !currentQuestion.selected_option;

                      return (
                        <button
                          className={`option-card option-card--large ${option.isUtilityOption ? "option-card--utility" : ""} ${isSelected ? "selected" : ""} ${isMissing ? "missing" : ""}`}
                          key={option.key}
                          onClick={() => onSaveAnswer(currentQuestion.id, option.key)}
                          type="button"
                        >
                          {!option.isUtilityOption ? (
                            <span className="option-card__key option-card__key--large">{option.key}</span>
                          ) : null}
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
