import { ProgressHeader } from "../ui";

export function CompletionScreen({ answeredCount, completionDate, protocolNumber, totalQuestions, onReset }) {
  return (
    <section className="stage-screen">
      <ProgressHeader
        leftText={`${answeredCount} de ${totalQuestions} questoes respondidas`}
        rightText={`${Math.max(totalQuestions - answeredCount, 0)} questoes restantes`}
        progress={100}
      />
      <div className="completion-layout">
        <div className="panel panel--completion">
          <div className="panel__content panel__content--completion">
            <div className="success-mark" aria-hidden="true">
              V
            </div>
            <h1>Avaliacao concluida com sucesso</h1>
            <p className="lead">
              Recebemos suas respostas. Voce pode encerrar esta sessao com tranquilidade. Se necessario,
              guarde os dados de referencia abaixo.
            </p>

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
                  <strong>Envio confirmado</strong>
                </div>
              </div>
            </div>

            <div className="action-row">
              <button className="button button--primary" onClick={onReset} type="button">
                Enviar respostas
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
