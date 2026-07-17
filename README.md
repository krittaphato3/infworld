# Infinite Realms

**Prompt-to-Playable-Game Engine**

```
  ___       __                __        ______              
 |_ _|_ __ / _| ___  _ __ __ \ \      / /___ \ _ __   ___ 
  | || '_ \ |_ / _ \| '__/ _` \ \ /\ / /  __)| '_ \ / _ \
  | || | | |  _| (_) | | | (_| |\ V  V /  / __/| | | |  __/
 |___|_| |_|_|  \___/|_|  \__, | \_/\_/  |_____|_| |_|\___|
                           |___/                            
```

Turn any text description into a fully playable browser game powered by AI agents.

---

## Features

- **4-Agent Pipeline** -- Director, Asset, Engineer, and Assembler agents collaborate sequentially
- **Real-time Generation** -- Submit a prompt, get a playable Phaser.js game in minutes
- **Image & Audio Assets** -- Automatically generates sprites, backgrounds, and sound effects
- **Single-File Output** -- Each game is a self-contained HTML file served instantly
- **REST API** -- Programmatic access to the generation pipeline
- **Polished Frontend** -- Dark neon-themed UI with loading states and embedded game player

---

## Prerequisites

- Python 3.11+
- An OpenAI API key (or any OpenAI-compatible endpoint)
- Sufficient credits for GPT-4o, DALL-E 3, and TTS usage

---

## Quick Start

```bash
# 1. Clone or download the project
cd InfWorld

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and set your real API keys

# 5. Run the server
python main.py
```

Open **http://localhost:8000** in your browser.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BASE_URL` | OpenAI-compatible API base URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | API key for chat completions | *(required)* |
| `LLM_MODEL` | Model for text generation | `gpt-4o` |
| `IMAGE_API_URL` | Image generation API base URL | `https://api.openai.com/v1` |
| `IMAGE_API_KEY` | API key for image generation | *(required for images)* |
| `IMAGE_MODEL` | Image model name | `dall-e-3` |
| `AUDIO_API_URL` | Audio generation API base URL | `https://api.openai.com/v1` |
| `AUDIO_API_KEY` | API key for audio generation | *(optional)* |
| `AUDIO_MODEL` | Audio model name | `tts-1` |
| `APP_HOST` | Server bind host | `0.0.0.0` |
| `APP_PORT` | Server bind port | `8000` |
| `GENERATED_DIR` | Output directory for game bundles | `generated` |

---

## Architecture

```
┌──────────────┐
│  Frontend    │  Single-page HTML + Tailwind
│  (Browser)   │
└──────┬───────┘
       │ POST /api/generate-game
       ▼
┌──────────────┐
│  FastAPI     │  main.py  --  REST endpoints + static serving
│  Server      │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│                  Pipeline                        │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  │ Director  │→ │  Asset   │→ │ Engineer │→ │Assembler │
│  │  Agent    │  │  Agent   │  │  Agent   │  │  Agent   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘
│                                                  │
│  GDD JSON    Image/Audio    Phaser.js JS    HTML File │
└──────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  generated/  │  {game_id}/index.html
│  directory   │  Served at /play/{game_id}
└──────────────┘
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve the frontend UI |
| `POST` | `/api/generate-game` | Submit a game prompt and start generation |
| `GET` | `/api/game/{game_id}` | Check the generation status of a game |
| `GET` | `/play/{game_id}` | Serve the generated game HTML |
| `GET` | `/static/{path}` | Serve static frontend assets |

---

## How It Works

1. **Director Agent** receives the user's free-text prompt and produces a structured Game Design Document (GDD) as JSON -- title, mechanics, controls, win/loss conditions, and a list of required assets.

2. **Asset Agent** iterates over the GDD asset list and generates each one -- images via DALL-E (or compatible API) and audio via TTS (with graceful fallback to placeholder audio).

3. **Engineer Agent** feeds the complete GDD and all asset URLs to the LLM, instructing it to produce a fully working Phaser.js 3 game script that integrates every asset and implements all mechanics.

4. **Assembler Agent** wraps the generated JavaScript in a complete HTML file with Phaser loaded from CDN and writes it to `generated/{game_id}/index.html`.

5. The frontend embeds the game in an iframe at `/play/{game_id}` -- ready to play immediately.

---

## Project Structure

```
InfWorld/
├── .env.example          # Environment variable template
├── .env                  # Active configuration (git-ignored)
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── main.py               # FastAPI entry point
├── config.py             # Centralized settings from .env
├── client.py             # OpenAI-compatible LLM client
├── models.py             # Pydantic request/response/state models
├── pipeline.py           # Agent orchestration
├── agents/
│   ├── __init__.py       # Exports all agent classes
│   ├── base.py           # BaseAgent abstract class
│   ├── director.py       # GDD generation
│   ├── asset.py          # Image/audio generation
│   ├── engineer.py       # Phaser.js code generation
│   └── assembler.py      # HTML bundling
├── static/
│   └── index.html        # Single-page frontend
└── generated/            # Runtime output directory
    └── .gitkeep
```

---

## License

MIT
