<!-- capsule-v2 -->
# Fullscreen scroll overlay — how does a custom TUI surface get scrolling, spinner, and clean disposal?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the custom-overlay contract (render/handleInput/dispose), and how is the running-experiment row kept live?

## createFullscreenHandler — ui.custom overlay, 80ms spinner interval, clamped scrollOffset
**Path/Symbol:** `extensions/pi-autoresearch/src/ui/fullscreen.ts` — handler :56–232; state factory :34–40; `clearFullscreen` :45–51; title fitter :15–17.
**Signature:** `extCtx.ui.custom<void>((tui, theme, _kb, done) => ({ render(width), handleInput(data), invalidate(), dispose() }), { overlay: true, overlayOptions: { width:'95%', maxHeight:'90%', anchor:'center' } })`.
**Data Shape:** FullscreenState `{overlayTui, spinnerInterval, spinnerFrame}`; viewport = `max(4, floor(rows×0.9) − 5 chrome rows)`.

### Decisive source
```ts
uiState.spinnerInterval = setInterval(() => {
  uiState.spinnerFrame = (uiState.spinnerFrame + 1) % SPINNER.length;
  if (runtime.runningExperiment) tui.requestRender();   // animate ONLY while something runs
}, 80);
// handleInput: esc|q done() · j/k ±1 · u/d ±viewport · g/G top/bottom · scrollOffset clamped to [0,maxScroll]
```

**Flow:** shortcut (default ctrl+shift+x) → TUI-mode + has-results guards → open bordered overlay rendering the shared dashboard lines at section width → while an experiment runs, append a synthetic next-row with braille spinner + elapsed time (formatElapsed) and let the interval drive re-renders → keys adjust clamped offset → dispose clears BOTH overlay ref and interval. Footer shows `start-end/total • top|bottom|N%`.
**Invariant:** the spinner interval must ALWAYS be cleared on close (`clearFullscreen` from dispose AND off/clear command paths) or it leaks re-render ticks forever. Scroll clamp runs inside render (self-healing when content shrinks) as well as in input handling. The overlay reuses renderDashboardLines rather than a second renderer — one source of truth for content, two surfaces for chrome.
**Probe:** direct test `__tests__/unit/fullscreen-width.test.ts` pins `fitOverlayTitle` truncation behavior; anchors: `grep -n 'SPINNER' extensions/pi-autoresearch/src/ui/fullscreen.ts | wc -l` → 3 (:13 def, :80 modulo, :114 frame pick); `grep -n "overlay: true" extensions/pi-autoresearch/src/ui/fullscreen.ts` → :223.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "createFullscreenHandler requestRender scrollOffset SPINNER", limit: 10 });
```

## Verdict
Adopt the custom-surface contract (render/handleInput/dispose + guarded interval) verbatim for any host with an extensible TUI; adapt key bindings and chrome; omit the spinner if your host has no idle animation slot. Coverage caveat: only the title-fitter is direct-tested; interaction loop source-pinned.
