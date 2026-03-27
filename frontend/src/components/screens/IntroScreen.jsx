import { INTRO_FEATURES } from "../../content/stageContent";
import { Badge, InfoCard, ScreenTopBar } from "../ui";

function IntroPanel({ onStart, onBack, isBusy, isLocked }) {
  return (
    <div className="panel panel--side">
      <div className="panel__content panel__content--side">
        <h2>{isLocked ? "Avaliacao em revisao" : "Recomendacoes rapidas"}</h2>
        <p>
          {isLocked
            ? "Voce ja concluiu sua avaliacao e ela esta sendo revisada pela equipe Kodie."
            : "Organize seu ambiente antes de iniciar para manter o foco durante toda a etapa."}
        </p>

        <div className="highlight-box">
          <div className="highlight-box__icon" aria-hidden="true">
            {isLocked ? "!" : "*"}
          </div>
          <div>
            <h3>{isLocked ? "Proximo passo" : "Dica pratica"}</h3>
            <p>
              {isLocked
                ? "Quando a revisao for concluida, a equipe Kodie entrara em contato com voce."
                : "Procure um local silencioso, mantenha uma leitura continua e avance no seu ritmo."}
            </p>
          </div>
        </div>

        <div className="tag-row">
          <Badge>{isLocked ? "Envio concluido" : "Etapa curta e objetiva"}</Badge>
        </div>

        <div className="action-row">
          {!isLocked ? (
            <button className="button button--primary" onClick={onStart} disabled={isBusy} type="button">
              Iniciar avaliacao
            </button>
          ) : null}
          <button className="button button--secondary" onClick={onBack} type="button">
            Voltar
          </button>
        </div>
      </div>
    </div>
  );
}

export function IntroScreen({ assessmentStatus, isBusy, onLogout, onStart, onBack, screenError }) {
  const isLocked = assessmentStatus === "COMPLETED";

  return (
    <section className="stage-screen">
      <ScreenTopBar actionLabel="Sair" onAction={onLogout} />
      <div className="desktop-grid desktop-grid--topless">
        <div className="panel panel--content">
          <div className="panel__content">
            <p className="eyebrow">Antes da primeira questao</p>
            <h1>{isLocked ? "Sua avaliacao ja foi enviada" : "Veja como a avaliacao vai funcionar"}</h1>
            <p className="lead">
              {isLocked
                ? "Seu envio foi registrado com sucesso. Agora a avaliacao segue para revisao da equipe Kodie."
                : "Esta etapa prepara voce para responder com tranquilidade. Leia as orientacoes abaixo e inicie quando estiver pronto."}
            </p>

            {screenError ? <p className="feedback feedback--error">{screenError}</p> : null}

            <div className="info-stack">
              {INTRO_FEATURES.map((feature) => (
                <InfoCard icon={feature.icon} key={feature.title} title={feature.title}>
                  {feature.description}
                </InfoCard>
              ))}
            </div>
          </div>
        </div>

        <IntroPanel isBusy={isBusy} isLocked={isLocked} onStart={onStart} onBack={onBack} />
      </div>
    </section>
  );
}
