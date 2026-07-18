import { useState, useCallback } from 'react';

export function useGameState() {
  const [view, setView] = useState('landing');
  const [gameId, setGameId] = useState(null);
  const [gameTitle, setGameTitle] = useState('');
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [logs, setLogs] = useState([]);
  const [stages, setStages] = useState([
    { name: 'Director', status: 'pending', message: '' },
    { name: 'Architect', status: 'pending', message: '' },
    { name: 'Engineer', status: 'pending', message: '' },
    { name: 'Assembler', status: 'pending', message: '' },
  ]);

  const addLog = useCallback((log) => {
    setLogs((prev) => [
      ...prev,
      {
        time: new Date().toLocaleTimeString(),
        agent: log.agent || 'system',
        message: log.message || '',
        type: log.type || 'info',
      },
    ]);
  }, []);

  const updateStage = useCallback((stageName, status, message) => {
    setStages((prev) =>
      prev.map((s) =>
        s.name === stageName
          ? { ...s, status, message: message ?? s.message }
          : s
      )
    );
  }, []);

  const resetState = useCallback(() => {
    setView('landing');
    setGameId(null);
    setGameTitle('');
    setFiles([]);
    setSelectedFile(null);
    setFileContent('');
    setLogs([]);
    setStages([
      { name: 'Director', status: 'pending', message: '' },
      { name: 'Architect', status: 'pending', message: '' },
      { name: 'Engineer', status: 'pending', message: '' },
      { name: 'Assembler', status: 'pending', message: '' },
    ]);
  }, []);

  return {
    view,
    setView,
    gameId,
    setGameId,
    gameTitle,
    setGameTitle,
    files,
    setFiles,
    selectedFile,
    setSelectedFile,
    fileContent,
    setFileContent,
    logs,
    setLogs,
    stages,
    setStages,
    addLog,
    updateStage,
    resetState,
  };
}
