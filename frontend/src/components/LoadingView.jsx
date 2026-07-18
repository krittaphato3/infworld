export default function LoadingView({ stages, logs }) {
  return (
    <div className="loading-view">
      <div className="loading-glow" />
      <h2 className="loading-title">BUILDING YOUR GAME</h2>
      <div className="loading-stages">
        {stages.map((stage, i) => (
          <div key={i} className={`loading-stage ${stage.status}`}>
            <div className="stage-dot">
              {stage.status === 'done' ? '\u2713' : i + 1}
            </div>
            <div className="stage-info">
              <div className="stage-name">{stage.name}</div>
              <div className="stage-message">{stage.message || 'Waiting...'}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="loading-logs">
        {logs.slice(-8).map((log, i) => (
          <div key={i} className="loading-log">
            <span className="log-agent">[{log.agent}]</span> {log.message}
          </div>
        ))}
        {logs.length === 0 && (
          <div className="loading-log idle">Initializing agents...</div>
        )}
      </div>
    </div>
  );
}
