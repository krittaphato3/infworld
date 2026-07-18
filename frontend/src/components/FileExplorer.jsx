import { useState, useEffect } from 'react';
import { listFiles } from '../api/client';

export default function FileExplorer({ gameId, selectedFile, onSelectFile }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!gameId) {
      setFiles([]);
      setLoading(false);
      return;
    }

    let cancelled = false;

    setLoading(true);
    setError(null);

    listFiles(gameId)
      .then((data) => {
        if (!cancelled) {
          setFiles(data.files || []);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [gameId]);

  const getFileIcon = (name) => {
    if (name.endsWith('.html')) return '\u{1F310}';
    if (name.endsWith('.js')) return '\u{1F4DC}';
    if (name.endsWith('.css')) return '\u{1F3A8}';
    if (name.endsWith('.json')) return '\u{1F4CB}';
    return '\u{1F4C4}';
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="file-explorer">
      <div className="file-explorer-header">EXPLORER</div>
      <div className="file-tree">
        {loading ? (
          <div className="file-loading">Loading...</div>
        ) : error ? (
          <div className="file-loading error">{error}</div>
        ) : files.length === 0 ? (
          <div className="file-loading">No files</div>
        ) : (
          files.map((f) => (
            <div
              key={f.path}
              className={`file-item ${selectedFile === f.path ? 'active' : ''}`}
              onClick={() => onSelectFile(f.path)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectFile(f.path);
                }
              }}
            >
              <span className="file-icon">{getFileIcon(f.name)}</span>
              <span className="file-name">{f.name}</span>
              <span className="file-size">{formatSize(f.size)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
