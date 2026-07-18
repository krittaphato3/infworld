import { useEffect, useRef } from 'react';

export default function AgentLogs({ logs }) {
  const contentRef = useRef(null);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="agent-logs">
      <div className="agent-logs-header">AGENT LOGS</div>
      <div className="agent-logs-content" ref={contentRef}>
        {logs.length === 0 ? (
          <div className="agent-logs-empty">No logs yet</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`agent-log-entry ${log.type || 'info'}`}>
              <span className="log-time">{log.time}</span>
              <span className="log-agent">[{log.agent}]</span>
              <span className="log-message">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
