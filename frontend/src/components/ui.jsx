export function BrandMark() {
  return (
    <div className="brand-mark">
      <span className="brand-mark__icon" />
      <span>Kodie</span>
    </div>
  );
}

export function ProgressHeader({ leftText, rightText, progress }) {
  return (
    <header className="progress-header">
      <div className="progress-header__row">
        <div className="progress-header__left">
          <BrandMark />
          {leftText ? <span className="progress-header__step">{leftText}</span> : null}
        </div>
        {rightText ? <strong className="progress-header__percent">{rightText}</strong> : null}
      </div>
      <div className="progress-header__track" aria-hidden="true">
        <div className="progress-header__fill" style={{ width: `${progress}%` }} />
      </div>
    </header>
  );
}

export function HelpLink() {
  return (
    <button className="text-help" type="button">
      <span className="text-help__icon">?</span>
      Precisa de ajuda?
    </button>
  );
}

export function InfoCard({ icon, title, children }) {
  return (
    <article className="info-card">
      <div className="info-card__icon" aria-hidden="true">
        {icon}
      </div>
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
    </article>
  );
}

export function Badge({ children }) {
  return <span className="pill-badge">{children}</span>;
}
