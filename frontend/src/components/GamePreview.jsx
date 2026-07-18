export default function GamePreview({ gameId }) {
  if (!gameId) {
    return (
      <div className="game-preview empty">
        <div className="game-preview-placeholder">
          <p>No game loaded</p>
          <p className="text-secondary">Generate a game to see it here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="game-preview">
      <div className="game-preview-header">
        <span>Game Preview</span>
        <a
          href={`/play/${gameId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="game-preview-btn"
        >
          {'\u2197'} Fullscreen
        </a>
      </div>
      <iframe
        src={`/play/${gameId}`}
        className="game-preview-iframe"
        title="Game Preview"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}
