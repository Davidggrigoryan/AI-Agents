#!/usr/bin/env bash
# Simple helper to start the Ollama server on a given port.
PORT="${1:-11434}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not found" >&2
  exit 1
fi

export OLLAMA_PORT="$PORT"
nohup ollama serve >/dev/null 2>&1 &
echo "Ollama server started on port $PORT"
