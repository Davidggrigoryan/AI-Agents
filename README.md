# AI Agent Control Panel

This project provides a Tkinter-based control panel to manage simple AI agents
and their tasks.

The interface includes tabs for managing agents, chatting, and application settings:

- **Agents** – create or delete agents, set a prompt for their behavior, choose
  between cloud (OpenAI API) or local (Ollama) execution, and persist agent
  changes in `agents.json`.
- **Chat** – hold quick conversations with a selected agent, keep lightweight
  per-agent history, and clear the log when necessary.
- **Settings** – enter and persist an OpenAI API key and configure the port used
  for a local Ollama instance. Dedicated buttons can launch and stop the Ollama
  server using the bundled scripts.

## Usage

You can run the control panel by double-clicking the provided script for your
platform:

- **Windows:** `run_gui.bat`
- **Linux/macOS:** `run_gui.sh`

You can also launch it from a terminal:

```bash
python gui.py
```

The window allows you to create tasks, assign them to agents, and start or stop
agents. The layout roughly follows the provided mock‑up.

To start a local Ollama server outside of the GUI, run `run_ollama.sh` on
Linux/macOS or `run_ollama.bat` on Windows. The Settings tab also has
"Запустить Ollama" and "Остановить Ollama" buttons that trigger the respective
commands and update the status bar once the server responds.

## Streaming web demo

A lightweight Flask server (`server.py`) now proxies Ollama with token streaming and a
browser UI served from `/static`. To try it:

1. Install dependencies (Flask and requests) if needed: `pip install flask requests`.
2. Launch the server: `python server.py` (it starts a warm-up request automatically).
3. Open `http://localhost:8000` in a browser and submit a prompt.

The UI keeps the Ollama model warm for 5 minutes, streams tokens in real time, shows
progress (status text, elapsed time, tokens per second), and offers Cancel/Retry
buttons plus an "Укоротить ответ" control that halves `num_predict` for faster
follow-up generations.
