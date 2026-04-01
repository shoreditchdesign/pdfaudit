export function App() {
  return (
    <main className="app-shell">
      <section className="panel">
        <p className="eyebrow">Frontend Scaffold</p>
        <h1>UI intentionally stripped back</h1>
        <p className="lead">
          The active workflow now runs from the terminal. This frontend is being kept as a minimal
          rebuild scaffold for a future replacement UI.
        </p>
        <div className="callout">
          <p>Current preferred flow</p>
          <code>npm run audit -- target/audit-your-theme.txt</code>
        </div>
      </section>
    </main>
  );
}
