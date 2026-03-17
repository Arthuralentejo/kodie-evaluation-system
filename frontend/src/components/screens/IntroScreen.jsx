import { INTRO_FEATURES } from "../../content/stageContent";
import { Badge, InfoCard } from "../ui";

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

export function IntroScreen({ isBusy, onStart, onBack }) {
  return (
    <section className="stage-screen">
      <div className="desktop-grid desktop-grid--topless">
        <div className="panel panel--content">
          <div className="panel__content">
            <p className="eyebrow">Antes da primeira questao</p>
            <h1>Veja como a avaliacao vai funcionar</h1>
            <p className="lead">
              Esta etapa prepara voce para responder com tranquilidade. Leia as orientacoes abaixo e
              inicie quando estiver pronto.
            </p>

            <div className="info-stack">
              {INTRO_FEATURES.map((feature) => (
                <InfoCard icon={feature.icon} key={feature.title} title={feature.title}>
                  {feature.description}
                </InfoCard>
              ))}
            </div>
          </div>
        </div>

        <IntroPanel isBusy={isBusy} onStart={onStart} onBack={onBack} />
      </div>
    </section>
  );
}
