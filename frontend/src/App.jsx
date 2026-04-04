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
          assessmentStatus={flow.assessmentStatus}
          screenError={flow.screenError}
          onBack={flow.resetToStart}
          onLogout={flow.logout}
          onStart={() => flow.startAssessment(flow.selectedLevel)}
          completedAssessments={flow.completedAssessments}
          selectedLevel={flow.selectedLevel}
          onLevelChange={flow.setSelectedLevel}
        />
      </main>
    );
  }

  if (flow.stage === STAGES.QUESTIONS) {
    return (
      <main className="app-shell">
        <QuestionsScreen
          answeredCount={flow.answeredCount}
          currentIndex={flow.currentIndex}
          currentQuestion={flow.currentQuestion}
          isBusy={flow.isBusy}
          missingQuestionIds={flow.missingQuestionIds}
          onJumpToQuestion={(index) => flow.setCurrentIndex(Math.max(0, Math.min(flow.questions.length - 1, index)))}
          onLogout={flow.logout}
          onNext={() => flow.setCurrentIndex((value) => Math.min(flow.questions.length - 1, value + 1))}
          onFinish={flow.goToReview}
          onPrev={() => flow.setCurrentIndex((value) => Math.max(0, value - 1))}
          onSaveAnswer={flow.saveAnswer}
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
        isSubmitted={flow.stage === STAGES.COMPLETED}
        isSubmitting={flow.isSubmitting}
        onLogout={flow.logout}
        protocolNumber={flow.protocolNumber}
        screenError={flow.screenError}
        totalQuestions={flow.questions.length || 20}
        onReset={flow.resetToStart}
        onSubmit={flow.submitAssessment}
      />
    </main>
  );
}
