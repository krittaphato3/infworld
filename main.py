"""FastAPI application entry point for Infinite Realms."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from models import (
    APIStatus,
    ConfigResponse,
    ConfigUpdate,
    EditGameRequest,
    GamePrompt,
    GenerateResponse,
    GameStatusResponse,
)
from pipeline import run_pipeline, games

app = FastAPI(title="Infinite Realms", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the generated directory exists at startup
os.makedirs(settings.generated_dir, exist_ok=True)

# Serve generated game bundles
app.mount(
    "/generated",
    StaticFiles(directory=settings.generated_dir),
    name="generated",
)

# Serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Serve the single-page frontend."""
    return FileResponse("static/index.html")


@app.post("/api/generate-game", response_model=GenerateResponse)
async def generate_game(prompt: GamePrompt) -> GenerateResponse:
    """Accept a game prompt, run the agent pipeline, return a game_id."""
    if not prompt.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        state = await run_pipeline(prompt)
    except Exception as exc:
        print(f"[API] Game generation failed: {exc}")
        raise HTTPException(
            status_code=500, detail="Game generation failed. Please try again."
        )

    if state.status == "failed":
        raise HTTPException(status_code=500, detail=state.error)

    gdd_title = state.gdd.title if state.gdd else "Untitled"
    return GenerateResponse(
        game_id=state.game_id,
        status=state.status,
        message=f"Game '{gdd_title}' generated successfully!",
    )


@app.get("/api/game/{game_id}", response_model=GameStatusResponse)
async def get_game_status(game_id: str) -> GameStatusResponse:
    """Check the status of a game generation."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    state = games[game_id]
    return GameStatusResponse(
        game_id=state.game_id,
        status=state.status,
        error=state.error,
    )


@app.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return current configuration status (never expose API keys)."""
    from config import is_configured

    return ConfigResponse(
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_configured=is_configured(settings.llm_api_key),
        image_api_url=settings.image_api_url,
        image_model=settings.image_model,
        image_configured=is_configured(settings.image_api_key),
        audio_api_url=settings.audio_api_url,
        audio_model=settings.audio_model,
        audio_configured=is_configured(settings.audio_api_key),
        apis={
            "llm": APIStatus(
                configured=is_configured(settings.llm_api_key),
                optional=False,
                label="LLM (Text Generation)",
                description="Required. Powers the Director, Engineer, and Assembler agents.",
            ),
            "image": APIStatus(
                configured=is_configured(settings.image_api_key),
                optional=True,
                label="Image Generation (DALL-E / Stable Diffusion)",
                description="Optional. Generates game sprites and backgrounds. Without it, colored placeholders are used.",
            ),
            "audio": APIStatus(
                configured=is_configured(settings.audio_api_key),
                optional=True,
                label="Audio Generation (TTS / SFX)",
                description="Optional. Generates sound effects and music. Without it, placeholder audio is used.",
            ),
        },
    )


@app.post("/api/config", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate) -> ConfigResponse:
    """Update configuration at runtime. API keys are never returned."""
    from config import update_settings

    updates = update.model_dump(exclude_none=True)
    update_settings(updates)
    return await get_config()


@app.post("/api/edit-game", response_model=GenerateResponse)
async def edit_game_endpoint(request: EditGameRequest):
    """Edit an existing game with new instructions."""
    from pipeline import edit_game

    try:
        state = await edit_game(request.game_id, request.edit_prompt)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        print(f"[API] Game edit failed: {exc}")
        raise HTTPException(status_code=500, detail="Game edit failed. Please try again.")

    if state.status == "failed":
        raise HTTPException(status_code=500, detail=state.error)

    return GenerateResponse(
        game_id=state.game_id,
        status=state.status,
        message="Game updated successfully!",
    )


@app.post("/api/test-connection")
async def test_connection(api_type: str):
    """Test an API connection by sending a minimal request.

    api_type: "llm", "image", or "audio"
    """
    import httpx

    if api_type not in ("llm", "image", "audio"):
        raise HTTPException(status_code=400, detail="api_type must be 'llm', 'image', or 'audio'")

    try:
        if api_type == "llm":
            from client import llm_client
            resp = await llm_client.chat(
                messages=[{"role": "user", "content": "Reply with only the word OK"}],
                max_tokens=10,
                temperature=0,
            )
            return {"status": "ok", "message": f"Connected. Model responded: {resp[:50] or '(empty)'}"}

        elif api_type == "image":
            if not settings.image_api_key or settings.image_api_key.startswith("sk-your"):
                return {"status": "skip", "message": "Image API key not configured — will use placeholders"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{settings.image_api_url}/models",
                    headers={"Authorization": f"Bearer {settings.image_api_key}"},
                )
                if resp.status_code == 200:
                    return {"status": "ok", "message": "Image API connection successful"}
                return {"status": "error", "message": f"Image API returned {resp.status_code}"}

        elif api_type == "audio":
            if not settings.audio_api_key or settings.audio_api_key.startswith("sk-your"):
                return {"status": "skip", "message": "Audio API key not configured — will use placeholders"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{settings.audio_api_url}/models",
                    headers={"Authorization": f"Bearer {settings.audio_api_key}"},
                )
                if resp.status_code == 200:
                    return {"status": "ok", "message": "Audio API connection successful"}
                return {"status": "error", "message": f"Audio API returned {resp.status_code}"}

    except httpx.ConnectError:
        return {"status": "error", "message": f"Could not connect to {api_type} API server"}
    except httpx.TimeoutException:
        return {"status": "error", "message": f"{api_type} API connection timed out"}
    except Exception as exc:
        return {"status": "error", "message": f"{api_type} API test failed: {str(exc)[:100]}"}


@app.get("/play/{game_id}", response_class=HTMLResponse)
async def play_game(game_id: str) -> HTMLResponse:
    """Serve the generated game HTML."""
    # SECURITY: reject path traversal characters in game_id
    if "/" in game_id or "\\" in game_id or ".." in game_id:
        raise HTTPException(status_code=400, detail="Invalid game ID")

    game_path = os.path.join(settings.generated_dir, game_id, "index.html")

    # SECURITY: verify resolved path is still inside generated_dir
    real_generated = os.path.realpath(settings.generated_dir)
    real_game_path = os.path.realpath(game_path)
    if not real_game_path.startswith(real_generated + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(game_path):
        raise HTTPException(status_code=404, detail="Game not found or still generating")
    return FileResponse(game_path, media_type="text/html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=True)
