"""Minimal Flask backend providing streaming access to Ollama."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Iterator

import requests
from flask import Flask, Response, jsonify, request, send_from_directory

DEFAULT_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3")
DEFAULT_NUM_PREDICT = int(os.getenv("OLLAMA_DEFAULT_NUM_PREDICT", "512"))
CONFIG_PATH = Path("config.json")
AGENTS_PATH = Path("agents.json")


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            pass
    return {}


CONFIG = _load_config()
OLLAMA_PORT = str(CONFIG.get("ollama_port", os.getenv("OLLAMA_PORT", "11434")))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1")
OLLAMA_URL = f"{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["JSON_AS_ASCII"] = False

_warmup_started = False


def schedule_warmup() -> None:
    global _warmup_started
    if _warmup_started:
        return
    _warmup_started = True
    threading.Thread(target=warm_up_models, daemon=True).start()


@app.get("/")
def index() -> Response:
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/generate")
def generate() -> Response:
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    model = payload.get("model") or DEFAULT_MODEL
    keep_alive = payload.get("keep_alive") or DEFAULT_KEEP_ALIVE
    num_predict_raw = payload.get("num_predict")
    try:
        num_predict = int(num_predict_raw) if num_predict_raw is not None else DEFAULT_NUM_PREDICT
    except (TypeError, ValueError):
        return jsonify({"error": "num_predict must be an integer"}), 400
    if num_predict <= 0:
        num_predict = DEFAULT_NUM_PREDICT
    stream_flag = bool(payload.get("stream", True))

    ollama_request = {
        "prompt": prompt,
        "model": model,
        "keep_alive": keep_alive,
        "num_predict": num_predict,
        "stream": stream_flag,
    }

    for optional in ("system", "context", "options", "format", "template"):
        if optional in payload:
            ollama_request[optional] = payload[optional]
    app.logger.info("Proxying prompt to Ollama model=%s stream=%s", model, stream_flag)

    def stream_response() -> Iterator[str]:
        try:
            with requests.post(
                OLLAMA_URL,
                json=ollama_request,
                stream=stream_flag,
                timeout=(10, None if stream_flag else 30),
            ) as resp:
                resp.raise_for_status()

                if not stream_flag:
                    yield resp.text
                    return

                for raw_line in resp.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    try:
                        message = json.loads(raw_line)
                    except json.JSONDecodeError:
                        message = {"error": "invalid json from ollama", "raw": raw_line}
                    yield json.dumps(message, ensure_ascii=False) + "\n"
                    if message.get("done"):
                        break
        except requests.RequestException as exc:
            app.logger.exception("Error while talking to Ollama")
            error = {"error": str(exc)}
            yield json.dumps(error, ensure_ascii=False) + "\n"

    mimetype = "application/json" if not stream_flag else "application/json"
    return Response(stream_response(), mimetype=mimetype)


def _discover_models() -> set[str]:
    models: set[str] = set()
    env_models = os.getenv("OLLAMA_WARM_MODELS")
    if env_models:
        models.update(m.strip() for m in env_models.split(",") if m.strip())

    if AGENTS_PATH.exists():
        try:
            with AGENTS_PATH.open("r", encoding="utf-8") as fh:
                agents = json.load(fh)
            if isinstance(agents, list):
                for agent in agents:
                    if isinstance(agent, dict):
                        model = agent.get("model")
                        if isinstance(model, str) and model:
                            models.add(model)
        except json.JSONDecodeError:
            app.logger.warning("Failed to parse agents.json for warm-up")

    if not models:
        models.add(DEFAULT_MODEL)
    return models


def warm_up_models() -> None:
    models = _discover_models()
    if not models:
        return

    for model in models:
        try:
            app.logger.info("Warming up model %s", model)
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "prompt": "ping",
                    "model": model,
                    "stream": False,
                    "keep_alive": DEFAULT_KEEP_ALIVE,
                    "num_predict": 5,
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            app.logger.warning("Warm-up failed for %s: %s", model, exc)
        else:
            app.logger.info("Model %s warmed", model)


@app.before_first_request
def _trigger_warmup() -> None:
    schedule_warmup()


schedule_warmup()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
