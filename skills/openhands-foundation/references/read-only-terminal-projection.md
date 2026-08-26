<!-- capsule-v2 -->
# Read-only terminal projection — an event-sourced command store replayed into a disposed-safe xterm view

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How do you render a live agent terminal as a pure projection of streamed command events, safe against hidden-container fit crashes and remount history loss?

## Connected graph-selected seam
**Path/Symbol:** `src/hooks/use-terminal.ts` (212 L): `renderCommand` (12–30), `canFitTerminal` (37–71), `resolveTerminalForeground` (73–86), module-level `persistentLastCommandIndex` (:90), `useTerminal` (92–212) with mount-replay effect (139–172), incremental watermark effect (174–190), ResizeObserver→rAF→fit (192–209). Companion `src/utils/parse-terminal-output.ts:parseTerminalOutput` (17–28) strips the backend's `[Python Interpreter: …]` marker. Direct test: `__tests__/hooks/use-terminal.test.tsx` ("should render", "should render the commands", "should not call fit() when terminal.element is null"; file is parse_partial at :53 only — a fixture line, outside cited ranges).
**Signature:** `useTerminal(): React.RefObject<HTMLDivElement>` (attach to host); `canFitTerminal(terminal, fitAddon, container): boolean`; `parseTerminalOutput(raw: string): string`.
**Data Shape:** `Command { content: string; type: "input" | "output" }` from `useCommandStore` — the terminal never owns state, it renders the store.

### Decisive source
```ts
// Fit ladder — prevents "Cannot read properties of undefined (reading 'dimensions')":
const canFitTerminal = (terminalInstance, fitAddonInstance, containerElement) =>
  !!terminalInstance && !!fitAddonInstance && !!containerElement
  && window.getComputedStyle(containerElement).display !== "none"   // offsetParent null when hidden
  && containerElement.clientWidth > 0 && containerElement.clientHeight > 0
  && !!terminalInstance.element;                                    // set only after open()
new ResizeObserver(() => requestAnimationFrame(() => fitTerminalSafely())).observe(host);
// Watermark replay — mount replays ALL commands ($ prefix for inputs); later runs append ONLY new:
for (let i = lastCommandIndex.current; i < commands.length; i++) { ... }
lastCommandIndex.current = commands.length;
// Cleanup order matters: isDisposed=true BEFORE dispose so late observer frames cannot fit();
// module-level watermark survives unmounts (tab switches) and resets to 0 in cleanup.
```

**Flow:** agent command events land in a zustand command store → terminal host mounts → create xterm with `disableStdin:true`, cursor hidden via ANSI `\x1b[?25l`, transparent background because **canvas fillStyle cannot resolve CSS variables**, foreground resolved by measuring a hidden probe span of `var(--oh-surface-foreground)` with host-color fallback → full store replay on mount → incremental writes guarded by the watermark → resize path rAF-debounces before fit → user-typed input commands are skipped on stream render (`isUserInput`) since they were already echoed while typing, but still rendered during full replay.

**Invariant:** Terminal is disposable state: every mutation site checks `isDisposed`/`canFitTerminal` first; history lives in the store, so any remount reconstructs byte-identical scrollback from events alone; writes normalize `\n`→`\r\n` and skip empty content.

**Probe:** Executed this pass under `node --experimental-strip-types` importing the REAL `parse-terminal-output.ts` (exit 0): docstring example returns `"web_scraper.py"`; marker-less input passes through unchanged; unclosed-marker input passes through unchanged. Hook invariants verified by line-pinned content checks at HEAD + coverage `no_recorded_issue` on `src/hooks/use-terminal.ts`; vitest runner blocked this pass (no node_modules; clean read-only tree).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "terminal xterm write output", limit: 10 });
// executed this pass -> useTerminal 92-212, createTerminal 100-115, canFitTerminal 37-71,
// parseTerminalOutput src/utils/parse-terminal-output.ts 17-28
```

## Verdict
Adopt store-owned-history + watermark projection for any streaming console UI, the five-clause fit ladder verbatim, and the CSS-var color probing trick for canvas-based emitters. Adapt xterm addons/theme tokens to your stack. Omit the OpenHands-specific Python-interpreter marker parser unless your backend injects similar banners (then copy its tolerate-malformed pass-through posture instead of the marker itself). Coverage: `no_recorded_issue` (hook/parser); direct test file parse-partial at :53 recorded, outside cited behavior.
