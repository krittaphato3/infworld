import { useState } from 'react';

const EXAMPLES = [
  'A space invaders game with waves of aliens',
  'A platformer where you collect coins and avoid spikes',
  'A match-3 puzzle game with colorful gems',
  'A tower defense game with upgradeable turrets',
];

export default function LandingView({ onStart }) {
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);

  const handleStart = async () => {
    if (!prompt.trim() || generating) return;
    setGenerating(true);
    try {
      await onStart(prompt.trim());
    } finally {
      setGenerating(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleStart();
    }
  };

  return (
    <div className="landing-view">
      <div className="landing-glow" />
      <h1 className="landing-title">INFINITE REALMS</h1>
      <p className="landing-subtitle">AI-Powered Game Development IDE</p>
      <div className="landing-prompt-area">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your dream game..."
          rows={4}
          disabled={generating}
        />
        <button
          onClick={handleStart}
          disabled={!prompt.trim() || generating}
        >
          {generating ? 'Generating...' : 'Generate Game'}
        </button>
        <div className="landing-hint">Ctrl+Enter to generate</div>
      </div>
      <div className="landing-examples">
        <p className="landing-examples-label">Try these:</p>
        {EXAMPLES.map((ex, i) => (
          <button
            key={i}
            className="example-chip"
            onClick={() => setPrompt(ex)}
            disabled={generating}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
