import { AUTH_FEATURES } from '../../content/stageContent';
import { maskCpf, normalizeDateInput } from '../../utils/formatters';
import { HelpLink, InfoCard, Badge, ScreenTopBar } from '../ui';

function AuthPanel({
  cpf,
  birthDate,
  authError,
  isBusy,
  onCpfChange,
  onBirthDateChange,
  onSubmit,
}) {
  return (
    <div className="panel panel--form">
      <div className="panel__content">
        <h2>Informe seus dados</h2>
        <p>Preencha os campos abaixo para continuar para a proxima etapa.</p>

        <form className="form-stack" onSubmit={onSubmit}>
          <label htmlFor="cpf">CPF</label>
          <div className="field">
            <input
              id="cpf"
              value={cpf}
              onChange={(event) => onCpfChange(maskCpf(event.target.value))}
              inputMode="numeric"
              autoComplete="off"
              placeholder="000.000.000-00"
              required
            />
            <span className="field__icon" aria-hidden="true">
              U
            </span>
          </div>
          <small>Digite apenas numeros.</small>

          <label htmlFor="birth_date">Data de nascimento</label>
          <div className="field">
            <input
              id="birth_date"
              value={birthDate}
              onChange={(event) =>
                onBirthDateChange(normalizeDateInput(event.target.value))
              }
              inputMode="numeric"
              autoComplete="bday"
              placeholder="DD/MM/AAAA"
              required
            />
            <span className="field__icon" aria-hidden="true">
              C
            </span>
          </div>
          <small>Use o formato com dia, mes e ano.</small>

          {authError && <p className="feedback feedback--error">{authError}</p>}

          <button
            className="button button--primary button--wide"
            disabled={isBusy}
            type="submit"
          >
            {isBusy ? 'Validando...' : 'Continuar'}
          </button>
        </form>

        <HelpLink />
      </div>
    </div>
  );
}

export function AuthScreen({
  cpf,
  birthDate,
  authError,
  isBusy,
  onCpfChange,
  onBirthDateChange,
  onSubmit,
}) {
  return (
    <section className="stage-screen">
      <ScreenTopBar />
      <div className="desktop-grid desktop-grid--topless">
        <div className="panel panel--content">
          <div className="panel__content">
            <p className="eyebrow">Plataforma de avaliacao</p>
            <h1>Vamos comecar com sua identificacao</h1>
            <p className="lead">
              Use seus dados para acessar a jornada de avaliacao com seguranca.
              O processo e simples, direto e leva apenas alguns minutos.
            </p>

            <div className="info-stack">
              {AUTH_FEATURES.map((feature) => (
                <InfoCard
                  icon={feature.icon}
                  key={feature.title}
                  title={feature.title}
                >
                  {feature.description}
                </InfoCard>
              ))}
            </div>

            <div className="tag-row">
              <Badge>Sessao protegida</Badge>
              <Badge>Leitura rapida e objetiva</Badge>
            </div>
          </div>
        </div>

        <AuthPanel
          cpf={cpf}
          birthDate={birthDate}
          authError={authError}
          isBusy={isBusy}
          onCpfChange={onCpfChange}
          onBirthDateChange={onBirthDateChange}
          onSubmit={onSubmit}
        />
      </div>
    </section>
  );
}
