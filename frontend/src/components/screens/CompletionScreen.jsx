import { ScreenTopBar } from "../ui";

export function CompletionScreen({
  answeredCount,
  completionDate,
  isSubmitted,
  isSubmitting,
  onLogout,
  protocolNumber,
  screenError,
  totalQuestions,
  onReset,
  onSubmit,
}) {
  return (
    <section className="stage-screen">
      <ScreenTopBar actionLabel="Sair" onAction={onLogout} />
      <div className="completion-layout">
        <div className="panel panel--completion">
          <div className="panel__content panel__content--completion">
            <div className="success-mark" aria-hidden="true">
              V
            </div>
            <h1>{isSubmitted ? "Avaliacao concluida com sucesso" : "Revise e envie suas respostas"}</h1>
            <p className="lead">
              {isSubmitted
                ? "Recebemos suas respostas. Voce pode encerrar esta sessao com tranquilidade. Se necessario, guarde os dados de referencia abaixo."
                : "Voce chegou ao fim do questionario. Confira os dados da sessao abaixo e envie suas respostas para concluir a avaliacao."}
            </p>
            {screenError && <p className="feedback feedback--error">{screenError}</p>}

            <div className="session-card">
              <h2>Dados da sessao</h2>
              <div className="session-grid">
                <div>
                  <span>Numero de protocolo</span>
                  <strong>{protocolNumber}</strong>
                </div>
                <div>
                  <span>Data</span>
                  <strong>{completionDate.toLocaleDateString("pt-BR")}</strong>
                </div>
                <div>
                  <span>Etapas concluidas</span>
                  <strong>5 de 5</strong>
                </div>
                <div>
                  <span>Status</span>
                  <strong>{isSubmitted ? "Envio confirmado" : "Aguardando envio"}</strong>
                </div>
              </div>
            </div>

            <div className="action-row">
              <button
                className="button button--primary"
                disabled={isSubmitting}
                onClick={isSubmitted ? onReset : onSubmit}
                type="button"
              >
                {isSubmitted ? "Encerrar" : isSubmitting ? "Enviando..." : "Enviar respostas"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
