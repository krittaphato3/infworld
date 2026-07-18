"""FastAPI application entry point for Infinite Realms."""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from models import (
    APIStatus,
    ConfigResponse,
    ConfigUpdate,
    EditGameRequest,
    GamePrompt,
    GameSummary,
    GamesListResponse,
    GenerateResponse,
    GameStatusResponse,
)
from pipeline import (
    run_pipeline,
    run_pipeline_director,
    run_pipeline_architect,
    run_pipeline_engineer,
    run_pipeline_assembler,
    games,
)

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

# Serve the React frontend build
dist_dir = os.path.join(os.path.dirname(__file__), "static", "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Serve the React frontend."""
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Fallback to old static frontend
    return FileResponse("static/index.html")


@app.get("/old", response_class=HTMLResponse)
async def old_ui() -> HTMLResponse:
    """Serve the legacy static frontend."""
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


@app.get("/api/generate-stream")
async def generate_game_stream(prompt: str):
    """Stream game generation progress via Server-Sent Events."""
    import json as _json

    async def event_generator():
        game_id = str(__import__("uuid").uuid4())[:8]
        yield f"data: {_json.dumps({'type': 'started', 'game_id': game_id})}\n\n"

        # Stage 1: Director
        yield f"data: {_json.dumps({'type': 'stage', 'stage': 0, 'name': 'Director', 'message': 'Analyzing your game idea and creating a design document...'})}\n\n"
        try:
            state = await run_pipeline_director(game_id, prompt)
            yield f"data: {_json.dumps({'type': 'stage_complete', 'stage': 0, 'title': state.gdd.title if state.gdd else 'Untitled', 'genre': getattr(state.gdd, 'genre', 'unknown') if state.gdd else 'unknown', 'assets': len(state.assets)})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Stage 2: Architect
        yield f"data: {_json.dumps({'type': 'stage', 'stage': 1, 'name': 'Architect', 'message': 'Building game skeleton with BootScene and texture generation...'})}\n\n"
        try:
            state = await run_pipeline_architect(state)
            yield f"data: {_json.dumps({'type': 'stage_complete', 'stage': 1, 'skeleton_size': len(state.game_js)})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Stage 3: Engineer
        yield f"data: {_json.dumps({'type': 'stage', 'stage': 2, 'name': 'Engineer', 'message': 'Implementing game mechanics, player controls, and AI...'})}\n\n"
        try:
            state = await run_pipeline_engineer(state)
            yield f"data: {_json.dumps({'type': 'stage_complete', 'stage': 2, 'code_size': len(state.game_js)})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Stage 4: Assembler
        yield f"data: {_json.dumps({'type': 'stage', 'stage': 3, 'name': 'Assembler', 'message': 'Bundling HTML and saving game files...'})}\n\n"
        try:
            state = await run_pipeline_assembler(state)
            yield f"data: {_json.dumps({'type': 'stage_complete', 'stage': 3})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        yield f"data: {_json.dumps({'type': 'completed', 'game_id': state.game_id, 'title': state.gdd.title if state.gdd else 'Untitled'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/download/{game_id}")
async def download_game(game_id: str):
    """Download the generated game HTML file."""
    if "/" in game_id or "\\" in game_id or ".." in game_id:
        raise HTTPException(status_code=400, detail="Invalid game ID")

    html_path = os.path.join(settings.generated_dir, game_id, "index.html")

    real_generated = os.path.realpath(settings.generated_dir)
    real_game_path = os.path.realpath(html_path)
    if not real_game_path.startswith(real_generated + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Game not found")

    title = "game"
    meta_path = os.path.join(settings.generated_dir, game_id, "meta.json")
    if os.path.exists(meta_path):
        import json as _json
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = _json.load(f)
        title = meta.get("title", "game").lower().replace(" ", "_")

    return FileResponse(
        html_path,
        media_type="text/html",
        filename=f"{title}.html",
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


@app.get("/api/games", response_model=GamesListResponse)
async def list_games(
    sort: str = "newest",
    search: str = "",
) -> GamesListResponse:
    """List all generated games by scanning the filesystem."""
    import json as _json
    import re
    game_list = []
    generated_dir = settings.generated_dir

    if not os.path.exists(generated_dir):
        return GamesListResponse(games=[], total=0)

    for game_id in os.listdir(generated_dir):
        game_dir = os.path.join(generated_dir, game_id)
        if not os.path.isdir(game_dir):
            continue
        meta_path = os.path.join(game_dir, "meta.json")
        html_path = os.path.join(game_dir, "index.html")

        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = _json.load(f)
                title = meta.get("title", "Untitled")
                prompt = meta.get("prompt", "")
                created_at = meta.get("created_at", "")
                asset_count = meta.get("asset_count", 0)
                status = meta.get("status", "completed")
            except Exception:
                continue
        elif os.path.exists(html_path):
            title = "Untitled"
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read(2000)
                m = re.search(r"<title>(.*?)</title>", content)
                if m:
                    title = m.group(1)
            except Exception:
                pass
            mtime = os.path.getmtime(html_path)
            created_at = datetime.fromtimestamp(mtime).isoformat()
            prompt, asset_count, status = "", 0, "completed"
            meta = {"game_id": game_id, "prompt": prompt, "title": title,
                    "status": status, "created_at": created_at, "asset_count": asset_count}
            try:
                with open(meta_path, "w", encoding="utf-8") as f:
                    _json.dump(meta, f)
            except Exception:
                pass
        else:
            continue

        if search and search.lower() not in title.lower() and search.lower() not in prompt.lower():
            continue

        game_list.append(GameSummary(
            game_id=game_id, title=title, prompt=prompt[:200],
            status=status, created_at=created_at, asset_count=asset_count,
        ))

    if sort == "oldest":
        game_list.sort(key=lambda g: g.created_at)
    else:
        game_list.sort(key=lambda g: g.created_at, reverse=True)

    return GamesListResponse(games=game_list, total=len(game_list))


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


@app.get("/api/files/{game_id}")
async def list_game_files(game_id: str):
    """List all files in a generated game directory."""
    # Path traversal protection
    if "/" in game_id or "\\" in game_id or ".." in game_id:
        raise HTTPException(status_code=400, detail="Invalid game ID")
    game_dir = os.path.join(settings.generated_dir, game_id)

    real_generated = os.path.realpath(settings.generated_dir)
    real_game_dir = os.path.realpath(game_dir)
    if not real_game_dir.startswith(real_generated + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(game_dir):
        raise HTTPException(status_code=404, detail="Game not found")

    files = []
    for root, dirs, filenames in os.walk(game_dir):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, game_dir)
            size = os.path.getsize(fpath)
            files.append({
                "path": rel_path,
                "name": fname,
                "size": size,
                "type": "file",
            })

    return {"game_id": game_id, "files": files}


@app.get("/api/files/{game_id}/{file_path:path}")
async def get_file_content(game_id: str, file_path: str):
    """Get the content of a specific file in a game directory."""
    # Path traversal protection
    if ".." in game_id or ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    game_dir = os.path.join(settings.generated_dir, game_id)
    real_generated = os.path.realpath(settings.generated_dir)
    real_game_dir = os.path.realpath(game_dir)
    if not real_game_dir.startswith(real_generated + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")

    full_path = os.path.join(game_dir, file_path)
    real_full = os.path.realpath(full_path)
    if not real_full.startswith(real_generated + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".md": "text/markdown",
        ".txt": "text/plain",
    }

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        import base64
        with open(full_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        return {"path": file_path, "content": content, "encoding": "base64", "mime": content_types.get(ext, "application/octet-stream")}

    return {"path": file_path, "content": content, "encoding": "utf-8", "mime": content_types.get(ext, "text/plain"), "size": os.path.getsize(full_path)}


@app.get("/api/game/{game_id}/meta")
async def get_game_meta(game_id: str):
    """Get metadata for a specific game."""
    import json as _json
    meta_path = os.path.join(settings.generated_dir, game_id, "meta.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Game not found")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = _json.load(f)
    return meta


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=True)
