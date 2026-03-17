import { CompletionScreen } from "./components/screens/CompletionScreen";
import { AuthScreen } from "./components/screens/AuthScreen";
import { IntroScreen } from "./components/screens/IntroScreen";
import { QuestionsScreen } from "./components/screens/QuestionsScreen";
import { STAGES } from "./config";
import { useAssessmentFlow } from "./hooks/useAssessmentFlow";

export function App() {
  const flow = useAssessmentFlow();

  if (flow.stage === STAGES.AUTH) {
    return (
      <main className="app-shell">
        <AuthScreen
          cpf={flow.cpf}
          birthDate={flow.birthDate}
          authError={flow.authError}
          isBusy={flow.isBusy}
          onCpfChange={flow.setCpf}
          onBirthDateChange={flow.setBirthDate}
          onSubmit={flow.login}
        />
      </main>
    );
  }

  if (flow.stage === STAGES.INTRO) {
    return (
      <main className="app-shell">
        <IntroScreen
          isBusy={flow.isBusy}
          onBack={flow.resetToStart}
          onStart={() => flow.setStage(STAGES.QUESTIONS)}
        />
      </main>
    );
  }

  if (flow.stage === STAGES.QUESTIONS) {
    return (
      <main className="app-shell">
        <QuestionsScreen
          answeredCount={flow.answeredCount}
          answerStates={flow.answerStates}
          currentIndex={flow.currentIndex}
          currentQuestion={flow.currentQuestion}
          isBusy={flow.isBusy}
          isSubmitting={flow.isSubmitting}
          missingQuestionIds={flow.missingQuestionIds}
          onNext={() => flow.setCurrentIndex((value) => Math.min(flow.questions.length - 1, value + 1))}
          onPrev={() => flow.setCurrentIndex((value) => Math.max(0, value - 1))}
          onSaveAnswer={flow.saveAnswer}
          onSelectQuestion={flow.setCurrentIndex}
          onSubmit={flow.submitAssessment}
          questions={flow.questions}
          screenError={flow.screenError}
        />
      </main>
    );
  }

  return (
    <main className="app-shell">
      <CompletionScreen
        answeredCount={flow.answeredCount}
        completionDate={flow.completionDate}
        protocolNumber={flow.protocolNumber}
        totalQuestions={flow.questions.length || 20}
        onReset={flow.resetToStart}
      />
    </main>
  );
}
