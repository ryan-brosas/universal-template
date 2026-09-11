<!-- capsule-v2 -->
# Headless capture renderer (server-side xterm) — how do you give REST/CLI/agent callers a clean, ANSI-processed pane grid when terminal emulation normally lives in the browser?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you run @xterm/headless on a server so raw PTY bytes become readable cell text + SGR-only snapshots, without the browser's xterm.js owning the screen?

## Flow-controlled write pump
**Path/Symbol:** `packages/server/src/capture-renderer.ts:CaptureRenderer` (33–235); write path `write` (53–64) → `pump` (66–90) → `resolveFlushWaiters` (92–99) → `flush` (101–107); backlog gauge `queuedBytes` (109–111).
**Signature:** `class CaptureRenderer { constructor(cols: number, rows: number, scrollback = CAPTURE_RENDERER_SCROLLBACK /*10_000*/); write(data: string): void; flush(): Promise<void>; get queuedBytes(): number; }`
**Data Shape:** `pendingChunks: string[]` coalesced every 256 chunks (`CAPTURE_RENDERER_PENDING_CHUNK_COMPACT_COUNT`, constants.ts:908); `pendingByteLength` / `queuedByteLengthValue` track UTF-8 **bytes**, not chars; monotonic `enqueuedSequence` / `completedSequence`; `flushWaiters: { resolve, targetSequence }[]`.

### Decisive source
```ts
// packages/server/src/capture-renderer.ts:29-33 (design comment)
// The hibernation renderer is always on; capture-pane renderers are created
// lazily. Both receive live PTY output. xterm parses asynchronously, so keep one
// write in flight, coalesce the next batch, and expose its byte backlog to PTY
// flow control instead of retaining one Promise closure per PTY fragment.
...
// :85-89 — a synchronous throw inside the parser must not wedge the pump
try {
  this.terminal.write(data, finish);
} catch {
  finish();
}
```

**Flow:** `write()` pushes the chunk, bumps the sequence, compacts at 256 chunks, pumps → `pump()` takes ALL pending chunks as one batch only if no write is in flight → xterm's async callback fires `finish()`: clears in-flight flag, decrements queued bytes by the batch's byte length, advances `completedSequence`, resolves waiters, re-pumps → `flush()` captures `enqueuedSequence` NOW and resolves when `completedSequence >= targetSequence` (already-drained ⇒ resolved immediately).
**Invariant:** exactly one parser write in flight; `queuedBytes` is byte-accurate across UTF-8 multibyte chunks (test feeds 300 × `"é"`), which is what makes it safe to feed into PTY flow control; `flush()` is sequence-scoped — writes arriving after the flush call do NOT extend the wait; disposal releases all waiters and zeroes queued bytes.
**Probe:** `packages/server/tests/capture-renderer.test.ts::"coalesces parser input and accounts for queued UTF-8 bytes"` (:49 — queuedBytes equals Buffer.byteLength before flush, 0 after), `::"releases queued bytes and flush barriers on disposal"` (:65).

## Pane readout, exec slicing, viewport hit-test
**Path/Symbol:** `capture(lines?)` (125–137, tmux `capture-pane -p` semantics); `findRow(needle)` (164–171); `extractBetween(startRow,endRow)` (179–191); `findTextInViewport(needle)` (200–211); resize guard (113–118).
**Signature:** `capture(lines?: number): string; findRow(needle: string): number; extractBetween(startRow: number, endRow: number): string; findTextInViewport(needle: string): { col: number; row: number } | null`
**Data Shape:** `capture` reads the last `lines` rows of the ACTIVE buffer (default: visible viewport), trailing blank rows stripped. `extractBetween` slices strictly between marker rows (both exclusive); `startRow === -1` ⇒ fall back to 0 (start marker never printed — shell died instantly), `endRow === -1` ⇒ full buffer (timed out or exited). Viewport coordinates are viewport-relative with `row` counted from buffer.baseY — the coordinate system CDP mouse events and SGR mouse use.

### Decisive source
```ts
// packages/server/src/capture-renderer.ts:173-178 (marker-fallback contract)
// Slice the rendered rows strictly between `startRow` and `endRow` (exclusive
// of both) as plain text, trimming trailing blanks. A `startRow` of -1 falls
// back to 0 (the start marker never printed — shell exited immediately); an
// `endRow` of -1 falls back to the full buffer length (no end marker — timed
// out or the session exited). Used by exec to extract the command's output
// between its start and end markers.
```

**Flow (exec integration):** `SessionCommandExecutor.execute` wraps the command with unique random start/end marker printfs, accumulates raw output up to a cap, then replays it through an EPHEMERAL CaptureRenderer (`buildExecResult`, session-command-executor.ts:232–247, scrollback `EXEC_EPHEMERAL_SCROLLBACK=10_000`) — fresh, not the persistent renderer, so each exec's output stays isolated and its markers sit near the buffer bottom — then `findRow` both markers and `extractBetween`. Persistent per-session renderers are created lazily by `ensureCaptureRenderer` (:106–114): seeded from `snapshotScrollback()` then `await flush()` BEFORE first use, so the first read lands on a populated grid instead of a blank one (xterm parses `write` on a timer). `waitFor` predicates test `renderer.capture()` after `flush()`.
**Invariant:** never read the grid synchronously after `write` — always `await flush()` first; ephemeral-per-exec renderers are disposed in `finally`; a `-1` marker row degrades to "everything before here", not an error.
**Probe:** `tests/capture-renderer.test.ts::"captures the normal buffer while a TUI owns the alternate buffer"` (:7); executor wiring read this session at session-command-executor.ts:23–27, 106–114, 232–247 (no dedicated upstream test for findRow/extractBetween — port with your own round-trip test).

## SGR-only hibernation snapshot (normal buffer under alt-screen TUI)
**Path/Symbol:** `captureNormal(maxLines, maxCodeUnits)` (142–159) + `utils/render-buffer-line-with-sgr.ts:renderBufferLineWithSgr` (99–123); limits `HIBERNATE_SCROLLBACK_LINES=2000`, `HIBERNATE_SCROLLBACK_MAX_CODE_UNITS=256*1024` (constants.ts:73–74); always-on instance built in `SessionManager.spawn` (session-manager.ts:481–486, pre-seeded from scrollback snapshot).
**Signature:** `captureNormal(maxLines: number, maxCodeUnits: number): string; renderBufferLineWithSgr(line: IBufferLine, cell: IBufferCell): string`
**Data Shape:** walks the NORMAL buffer bottom-up (alt-screen frames excluded by construction), stops at either limit, joins with `\r\n`, strips trailing blanks. Budget accounting counts UTF-16 code units including the 2-unit separator BEFORE pushing each row, so whole newest rows survive.

### Decisive source
```ts
// packages/server/src/capture-renderer.ts:139-141 (safety contract)
// Hibernation reads the normal buffer even while a TUI owns the alternate
// buffer. Only rendered text and SGR styling are exported; cursor movement,
// screen clearing, OSC, and terminal modes can never enter the snapshot.
```
```ts
// utils/render-buffer-line-with-sgr.ts:97-98, 113-114 (replayability trick)
// Convert an already-rendered xterm row into text plus SGR only. Resetting before
// every style run makes each row independently replayable if older rows are evicted.
...
rendered += style ? `${ESC}[0;${style}m` : RESET_SEQUENCE;
```

**Flow:** each cell's attributes (bold/dim/italic/underline/blink/inverse/strikethrough/overline + palette/RGB fg+bg) become one minimal SGR parameter list; style changes emit `\x1b[0;<params>m`, gaps emit reset; trailing reset closes the row. Snapshot round-trips: writing it back into a fresh renderer reproduces identical text AND styling (verified by the restored-renderer test).
**Invariant:** control state (cursor moves, clears, OSC, modes) can NEVER leak into a snapshot — only text + SGR; every style run is preceded by an explicit reset so any suffix of rows replays correctly; budget break keeps the NEWEST rows (bottom-up scan), never the oldest.
**Probe:** `tests/capture-renderer.test.ts::"retains rendered colors and styles as SGR-only output"` (:20 — exact SGR normalization incl. truecolor, snapshot re-writable, `captureNormal(100, len-1)` ⇒ ""), `::"keeps whole newest rows within both limits"` (:76 — maxLines=2 ⇒ "three\r\nfour"; maxCodeUnits=6 ⇒ "four"), `::"captures the normal buffer while a TUI owns the alternate buffer"` (:7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "CaptureRenderer write flush captureNormal queuedBytes", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.session-command-executor.SessionCommandExecutor.ensureCaptureRenderer", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the flow-control-aware write pump (byte-exact backlog + sequence-scoped flush barriers), the lazy seed-from-snapshot + flush-before-first-read pattern, the marker-row exec extraction with -1 fallbacks, and SGR-only normal-buffer snapshots with newest-rows-first budgets; adapt scrollback sizes, chunk-compaction count, and the CJS-via-createRequire import shim (see below) to your host; omit the CDP mouse coordinate coupling unless you also port viewport hit-testing consumers. Direct tests cover pump accounting, SGR fidelity, alt-screen isolation, and budget behavior; caveat: `findRow`/`extractBetween` have no dedicated upstream test file (executor-level coverage only) — add a round-trip test when porting.
**Host note:** `@xterm/headless` ships a broken ESM surface (CJS `main`, `module` field points nowhere), so load it via `createRequire(import.meta.url)` and cast to the package's own type shape — `import { Terminal }` throws at runtime even though types resolve (capture-renderer.ts:8–15 comment verified).
