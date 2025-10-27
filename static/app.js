const promptInput = document.querySelector('#prompt');
const modelInput = document.querySelector('#model');
const numPredictInput = document.querySelector('#num-predict');
const generateBtn = document.querySelector('#generate');
const cancelBtn = document.querySelector('#cancel');
const retryBtn = document.querySelector('#retry');
const shortenBtn = document.querySelector('#shorten');
const statusEl = document.querySelector('#status');
const timerEl = document.querySelector('#timer');
const hintEl = document.querySelector('#hint');
const metaEl = document.querySelector('#meta');
const responseEl = document.querySelector('#response');

let controller = null;
let timerHandle = null;
let silenceHandle = null;
let startTime = 0;
let lastBody = null;
let lastPrompt = '';
let tokensSeen = 0;
let lastModel = '';
let lastNumPredict = 512;
const SILENCE_THRESHOLD = 4000;

function setStatus(text) {
  statusEl.textContent = text;
}

function setHint(text) {
  hintEl.textContent = text;
}

function setMeta(text) {
  metaEl.textContent = text;
}

function resetResponse() {
  responseEl.textContent = '';
}

function renderToken(token) {
  responseEl.textContent += token;
}

function resetTimer() {
  if (timerHandle) {
    clearInterval(timerHandle);
    timerHandle = null;
  }
  timerEl.textContent = '0.0 с';
}

function startTimer() {
  resetTimer();
  startTime = performance.now();
  timerHandle = setInterval(() => {
    const elapsed = (performance.now() - startTime) / 1000;
    timerEl.textContent = `${elapsed.toFixed(1)} с`;
  }, 100);
}

function stopTimer() {
  if (timerHandle) {
    clearInterval(timerHandle);
    timerHandle = null;
  }
}

function scheduleSilenceWarning() {
  clearSilenceWarning();
  silenceHandle = setTimeout(() => {
    setHint('всё ещё думаю (модель ≈ медленно на длинных контекстах)');
  }, SILENCE_THRESHOLD);
}

function clearSilenceWarning() {
  if (silenceHandle) {
    clearTimeout(silenceHandle);
    silenceHandle = null;
  }
  setHint('');
}

function updateButtonsForRun(running) {
  generateBtn.disabled = running;
  cancelBtn.disabled = !running;
  retryBtn.disabled = running || !lastBody;
  shortenBtn.disabled = running;
}

async function streamGenerate(body) {
  controller = new AbortController();
  tokensSeen = 0;
  startTimer();
  scheduleSilenceWarning();
  setMeta('');
  setStatus('загружаю модель…');
  resetResponse();
  updateButtonsForRun(true);

  let timeoutHandle;
  try {
    const ctrl = controller;
    timeoutHandle = setTimeout(() => ctrl.abort(), 60_000);
    const resp = await fetch('/api/generate', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
      signal: ctrl.signal,
    });

    if (!resp.ok || !resp.body) {
      throw new Error(`Ошибка HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let running = true;
    let buffer = '';

    while (running) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let newlineIndex = buffer.indexOf('\n');
      while (newlineIndex !== -1) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        if (line.length) {
          let msg;
          try {
            msg = JSON.parse(line);
          } catch (err) {
            console.error('invalid json chunk', line, err);
            msg = null;
          }
          if (!msg) {
            newlineIndex = buffer.indexOf('\n');
            continue;
          }
          if (msg.response) {
            if (tokensSeen === 0) {
              setStatus('генерирую…');
            }
            tokensSeen += 1;
            renderToken(msg.response);
            const elapsed = (performance.now() - startTime) / 1000;
            if (elapsed > 0) {
              const tps = (tokensSeen / elapsed).toFixed(1);
              setStatus(`генерирую… ${tps} ток/с`);
            }
            scheduleSilenceWarning();
          }
          if (msg.error) {
            throw new Error(msg.error);
          }
          if (msg.warning) {
            setHint(msg.warning);
          }
          if (msg.done) {
            running = false;
            const elapsed = (performance.now() - startTime) / 1000;
            const tps = elapsed > 0 ? (tokensSeen / elapsed).toFixed(1) : '0.0';
            setMeta(`готово • ${tokensSeen} токенов • ${tps} ток/с`);
            setStatus('Готово');
            clearTimeout(timeoutHandle);
            buffer = '';
            break;
          }
        }
        newlineIndex = buffer.indexOf('\n');
      }
    }

    const remainder = buffer.trim();
    if (remainder) {
      try {
        const msg = JSON.parse(remainder);
        if (msg.response) {
          if (tokensSeen === 0) {
            setStatus('генерирую…');
          }
          tokensSeen += 1;
          renderToken(msg.response);
        }
        if (msg.done) {
          const elapsed = (performance.now() - startTime) / 1000;
          const tps = elapsed > 0 ? (tokensSeen / elapsed).toFixed(1) : '0.0';
          setMeta(`готово • ${tokensSeen} токенов • ${tps} ток/с`);
          setStatus('Готово');
          clearTimeout(timeoutHandle);
        }
      } catch (err) {
        console.error('invalid json chunk', remainder, err);
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      setStatus('Отменено');
      setMeta('');
    } else {
      console.error(error);
      setStatus('Ошибка генерации');
      setMeta(error.message || String(error));
    }
  } finally {
    updateButtonsForRun(false);
    stopTimer();
    clearSilenceWarning();
    controller = null;
    clearTimeout(timeoutHandle);
  }
}

function gatherBody(overrides = {}) {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    throw new Error('Введите запрос');
  }
  const model = (modelInput.value || '').trim();
  let numPredict = Number(numPredictInput.value);
  if (!Number.isFinite(numPredict) || numPredict <= 0) {
    numPredict = 512;
  }
  numPredictInput.value = String(numPredict);
  lastModel = model;
  lastNumPredict = numPredict;
  modelInput.value = model;
  return {
    prompt,
    model: model || undefined,
    stream: true,
    keep_alive: '5m',
    num_predict: numPredict,
    ...overrides,
  };
}

function runGeneration(customBody = null) {
  try {
    let body;
    if (customBody) {
      body = { ...customBody };
      if (typeof body.num_predict === 'number') {
        lastNumPredict = body.num_predict;
        numPredictInput.value = String(body.num_predict);
      }
      if (typeof body.model === 'string') {
        lastModel = body.model;
        modelInput.value = body.model;
      } else if (!body.model) {
        lastModel = '';
        modelInput.value = '';
      }
    } else {
      body = gatherBody();
    }
    body.stream = true;
    body.keep_alive = body.keep_alive || '5m';
    if (typeof body.num_predict === 'number' && body.num_predict > 0) {
      lastNumPredict = body.num_predict;
    }
    if (typeof body.model === 'string') {
      lastModel = body.model;
    } else if (!body.model) {
      lastModel = '';
    }
    const sanitized = { ...body };
    if (!sanitized.model) {
      delete sanitized.model;
    }
    let snapshot;
    try {
      snapshot = typeof structuredClone === 'function' ? structuredClone(sanitized) : JSON.parse(JSON.stringify(sanitized));
    } catch (cloneError) {
      console.warn('Falling back to shallow copy for history', cloneError);
      snapshot = { ...sanitized };
    }
    lastBody = snapshot;
    lastPrompt = sanitized.prompt;
    streamGenerate(sanitized);
  } catch (err) {
    setStatus('Ошибка ввода');
    setMeta(err.message || String(err));
  }
}

generateBtn.addEventListener('click', () => {
  runGeneration();
});

cancelBtn.addEventListener('click', () => {
  if (controller) {
    controller.abort();
  }
});

retryBtn.addEventListener('click', () => {
  if (!lastBody) {
    return;
  }
  promptInput.value = lastPrompt;
  modelInput.value = lastModel;
  numPredictInput.value = String(lastNumPredict);
  runGeneration();
});

shortenBtn.addEventListener('click', () => {
  const current = Number(numPredictInput.value) || 512;
  const next = Math.max(32, Math.floor(current / 2));
  numPredictInput.value = String(next);
  lastNumPredict = next;
  if (lastBody) {
    lastBody.num_predict = next;
  }
  setHint(`num_predict уменьшен до ${next}`);
});


window.addEventListener('beforeunload', () => {
  if (controller) {
    controller.abort();
  }
});

// Allow pressing Ctrl+Enter to trigger generation
document.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    if (!generateBtn.disabled) {
      runGeneration();
    }
  }
});

