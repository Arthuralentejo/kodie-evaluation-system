import { useState } from 'react';
import { INTRO_FEATURES } from '../../content/stageContent';
import { Badge, InfoCard, ScreenTopBar } from '../ui';

const LEVELS = [
  { value: 'iniciante', label: 'Iniciante' },
  { value: 'junior', label: 'Júnior' },
  { value: 'pleno', label: 'Pleno' },
  { value: 'senior', label: 'Sênior' },
  { value: 'geral', label: 'Geral' },
];

const LEVEL_LABELS = {
  iniciante: 'Iniciante',
  junior: 'Júnior',
  pleno: 'Pleno',
  senior: 'Sênior',
  geral: 'Geral',
};

function formatDatePtBR(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function OverrideConfirmModal({ level, onConfirm, onCancel }) {
  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="modal">
        <h2 id="modal-title">Iniciar nova avaliação?</h2>
        <p>
          Você já possui uma avaliação concluída. Ao iniciar uma nova avaliação
          no nível <strong>{LEVEL_LABELS[level] || level}</strong>, a avaliação
          anterior será arquivada e apenas esta passará a ser a válida.
        </p>
        <p className="modal__note">
          Seu histórico de avaliações anteriores será preservado.
        </p>
        <div className="modal__actions">
          <button
            className="button button--primary"
            onClick={onConfirm}
            type="button"
          >
            Confirmar
          </button>
          <button
            className="button button--secondary"
            onClick={onCancel}
            type="button"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

function LevelPicker({ selectedLevel, onLevelChange, completedAssessments }) {
  const completedLevels = new Set(
    (completedAssessments || []).map((a) => a.level)
  );

  return (
    <div className="level-picker">
      {LEVELS.map(({ value, label }) => {
        const isCompleted = completedLevels.has(value);
        const isSelected = selectedLevel === value;
        let className = 'level-card';
        if (isSelected) className += ' level-card--selected';
        if (isCompleted) className += ' level-card--completed';

        return (
          <button
            key={value}
            type="button"
            className={className}
            onClick={() => onLevelChange(value)}
            disabled={isCompleted}
          >
            <span className="level-card__label">{label}</span>
            {isCompleted && (
              <span className="level-card__badge">Concluído</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function CompletedAssessmentsList({ completedAssessments }) {
  if (!completedAssessments || completedAssessments.length === 0) return null;

  return (
    <div className="completed-assessments">
      <h3>Avaliações concluídas</h3>
      <ul>
        {completedAssessments.map((assessment) => (
          <li
            key={assessment.assessment_id}
            className="completed-assessment-item"
          >
            <span className="completed-assessment-item__level">
              {LEVEL_LABELS[assessment.level] || assessment.level}
            </span>
            <span className="completed-assessment-item__date">
              {formatDatePtBR(assessment.completed_at)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function IntroPanel({
  onStart,
  onBack,
  isBusy,
  assessmentStatus,
  selectedLevel,
  onLevelChange,
  completedAssessments,
}) {
  const [showConfirm, setShowConfirm] = useState(false);
  const canPickLevel = assessmentStatus !== 'DRAFT';
  const hasActiveAssessment = assessmentStatus === 'COMPLETED';
  const startDisabled = isBusy || !selectedLevel;

  function handleStartClick() {
    if (hasActiveAssessment) {
      setShowConfirm(true);
    } else {
      onStart();
    }
  }

  function handleConfirm() {
    setShowConfirm(false);
    onStart();
  }

  return (
    <div className="panel panel--side">
      <div className="panel__content panel__content--side">
        <h2>Recomendações rápidas</h2>
        <p>
          Organize seu ambiente antes de iniciar para manter o foco durante toda
          a etapa.
        </p>

        <div className="highlight-box">
          <div className="highlight-box__icon" aria-hidden="true">
            *
          </div>
          <div>
            <h3>Dica prática</h3>
            <p>
              Procure um local silencioso, mantenha uma leitura contínua e
              avance no seu ritmo.
            </p>
          </div>
        </div>

        <div className="tag-row">
          <Badge>Etapa curta e objetiva</Badge>
        </div>

        {canPickLevel && (
          <div className="level-picker-section">
            <p className="level-picker-label">Escolha o nível da avaliação:</p>
            <LevelPicker
              selectedLevel={selectedLevel}
              onLevelChange={onLevelChange}
              completedAssessments={completedAssessments}
            />
          </div>
        )}

        <CompletedAssessmentsList completedAssessments={completedAssessments} />

        <div className="action-row">
          <button
            className="button button--primary"
            onClick={handleStartClick}
            disabled={startDisabled}
            type="button"
          >
            Iniciar avaliação
          </button>
          <button
            className="button button--secondary"
            onClick={onBack}
            type="button"
          >
            Voltar
          </button>
        </div>
      </div>

      {showConfirm && (
        <OverrideConfirmModal
          level={selectedLevel}
          onConfirm={handleConfirm}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </div>
  );
}

export function IntroScreen({
  assessmentStatus,
  isBusy,
  onLogout,
  onStart,
  onBack,
  screenError,
  completedAssessments,
  selectedLevel,
  onLevelChange,
}) {
  return (
    <section className="stage-screen">
      <ScreenTopBar actionLabel="Sair" onAction={onLogout} />
      <div className="desktop-grid desktop-grid--topless">
        <div className="panel panel--content">
          <div className="panel__content">
            <p className="eyebrow">Antes da primeira questão</p>
            <h1>Veja como a avaliação vai funcionar</h1>
            <p className="lead">
              Esta etapa prepara você para responder com tranquilidade. Leia as
              orientações abaixo e inicie quando estiver pronto.
            </p>

            {screenError ? (
              <p className="feedback feedback--error">{screenError}</p>
            ) : null}

            <div className="info-stack">
              {INTRO_FEATURES.map((feature) => (
                <InfoCard
                  icon={feature.icon}
                  key={feature.title}
                  title={feature.title}
                >
                  {feature.description}
                </InfoCard>
              ))}
            </div>
          </div>
        </div>

        <IntroPanel
          isBusy={isBusy}
          assessmentStatus={assessmentStatus}
          selectedLevel={selectedLevel}
          onLevelChange={onLevelChange}
          completedAssessments={completedAssessments}
          onStart={onStart}
          onBack={onBack}
        />
      </div>
    </section>
  );
}
