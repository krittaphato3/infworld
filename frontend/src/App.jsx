import { useCallback } from 'react';
import Sidebar from './components/Sidebar';
import CodeEditor from './components/CodeEditor';
import GamePreview from './components/GamePreview';
import LandingView from './components/LandingView';
import LoadingView from './components/LoadingView';
import AgentLogs from './components/AgentLogs';
import { useSSE } from './hooks/useSSE';
import { useGameState } from './hooks/useGameState';
import { getFileContent } from './api/client';
import './App.css';

function App() {
  const state = useGameState();

  const stageNames = ['Director', 'Architect', 'Engineer', 'Assembler'];

  const handleSSEEvent = useCallback(
    (data) => {
      // Backend sends: {type, stage, name, message, game_id, title, ...}
      const { type, stage, name, message, game_id, title, skeleton_size, code_size } = data;
      const agentName = name || data.agent || 'system';

      state.addLog({ agent: agentName, message: message || '', type: type || 'info' });

      if (type === 'stage' && stage !== undefined) {
        var stageName = stageNames[stage] || agentName;
        state.updateStage(stageName, 'active', message || 'Working...');
      }

      if (type === 'stage_complete' && stage !== undefined) {
        var stageName = stageNames[stage] || agentName;
        var extra = '';
        if (title) extra = ' — ' + title;
        if (skeleton_size) extra = ' (' + skeleton_size + ' chars)';
        if (code_size) extra = ' (' + code_size + ' chars)';
        state.updateStage(stageName, 'done', 'Complete' + extra);
      }

      if (type === 'completed' && game_id) {
        state.setGameId(game_id);
        if (title) state.setGameTitle(title);
        state.setView('ide');
      }

      if (type === 'error') {
        state.addLog({ agent: 'system', message: message || 'Unknown error', type: 'error' });
      }
    },
    [state]
  );

  const handleSSEError = useCallback(
    () => {
      state.addLog({ agent: 'system', message: 'Connection lost', type: 'error' });
    },
    [state]
  );

  const sse = useSSE('/api/generate-stream', handleSSEEvent, handleSSEError);

  const handleGenerate = useCallback(
    async (prompt) => {
      state.resetState();
      state.setView('loading');
      state.setGameTitle('Generating...');
      state.addLog({ agent: 'system', message: 'Starting generation...', type: 'info' });
      sse.connect(prompt);
    },
    [state, sse]
  );

  const handleSelectFile = useCallback(
    async (filePath) => {
      if (!state.gameId || !filePath) return;

      state.setSelectedFile(filePath);
      try {
        const data = await getFileContent(state.gameId, filePath);
        state.setFileContent(data.content || '');
      } catch (err) {
        state.setFileContent(`// Error loading file: ${err.message}`);
      }
    },
    [state]
  );

  if (state.view === 'landing') {
    return <LandingView onStart={handleGenerate} />;
  }

  if (state.view === 'loading') {
    return <LoadingView stages={state.stages} logs={state.logs} />;
  }

  return (
    <div className="ide-layout">
      <Sidebar
        gameId={state.gameId}
        gameTitle={state.gameTitle}
        selectedFile={state.selectedFile}
        onSelectFile={handleSelectFile}
      />
      <div className="ide-main">
        <div className="ide-top">
          <CodeEditor
            content={state.fileContent}
            fileName={state.selectedFile}
          />
          <div className="resize-handle" />
          <GamePreview gameId={state.gameId} />
        </div>
        <AgentLogs logs={state.logs} />
      </div>
    </div>
  );
}

export default App;
