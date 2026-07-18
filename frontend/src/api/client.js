const API_BASE = '';

export async function generateGame(prompt) {
  const resp = await fetch(`${API_BASE}/api/generate-game`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!resp.ok) throw new Error(`generateGame failed: ${resp.status}`);
  return resp.json();
}

export async function listFiles(gameId) {
  const resp = await fetch(`${API_BASE}/api/files/${gameId}`);
  if (!resp.ok) throw new Error(`listFiles failed: ${resp.status}`);
  return resp.json();
}

export async function getFileContent(gameId, filePath) {
  const resp = await fetch(`${API_BASE}/api/files/${gameId}/${filePath}`);
  if (!resp.ok) throw new Error(`getFileContent failed: ${resp.status}`);
  return resp.json();
}

export async function getGameMeta(gameId) {
  const resp = await fetch(`${API_BASE}/api/game/${gameId}/meta`);
  if (!resp.ok) throw new Error(`getGameMeta failed: ${resp.status}`);
  return resp.json();
}

export async function editGame(gameId, editPrompt) {
  const resp = await fetch(`${API_BASE}/api/edit-game`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ game_id: gameId, edit_prompt: editPrompt }),
  });
  if (!resp.ok) throw new Error(`editGame failed: ${resp.status}`);
  return resp.json();
}

export async function listGames(sort = 'newest', search = '') {
  const resp = await fetch(`${API_BASE}/api/games?sort=${sort}&search=${encodeURIComponent(search)}`);
  if (!resp.ok) throw new Error(`listGames failed: ${resp.status}`);
  return resp.json();
}
