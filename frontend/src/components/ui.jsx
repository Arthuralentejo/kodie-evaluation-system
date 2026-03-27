export function BrandMark() {
  return (
    <div className="brand-mark">
      <span className="brand-mark__icon" />
      <span>Kodie</span>
    </div>
  );
}

export function ScreenTopBar({ actionLabel, onAction }) {
  return (
    <header className="screen-topbar">
      <div className="screen-topbar__row">
        <BrandMark />
        <div className="screen-topbar__actions">
          {actionLabel && onAction ? (
            <button className="header-action" onClick={onAction} type="button">
              {actionLabel}
            </button>
          ) : null}
        </div>
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
