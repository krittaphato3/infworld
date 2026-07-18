import FileExplorer from './FileExplorer';

export default function Sidebar({ gameId, gameTitle, selectedFile, onSelectFile }) {
  return (
    <div className="ide-sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-logo">{'\u25C6'}</span>
        <span className="sidebar-title">Infinite Realms</span>
      </div>
      {gameTitle && (
        <div className="sidebar-game-title">{gameTitle}</div>
      )}
      <FileExplorer
        gameId={gameId}
        selectedFile={selectedFile}
        onSelectFile={onSelectFile}
      />
    </div>
  );
}
