<!-- capsule-v2 -->
# PTY session & output pipeline — how does terminal output reach the browser without corrupting TUIs or ballooning memory?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you pipe a node-pty session to WebSocket clients with flow control, framing, compression, and kitty-graphics handling that modern TUIs survive?

## PTY session lifecycle — titles never splice into the stream
**Path/Symbol:** `packages/server/src/session.ts:Session` (54–508); `onPtyOutput` (390–458); `snapshotScrollback` (363–365); `appendScrollback` (367–378).
**Signature:** `new Session(input: SpawnPtyInput)` extends `EventEmitter<SessionEvents>`; events: output/exit/title/cwd/foreground/notification/git-dirty/automation-exit/focus-reporting-changed.
**Data Shape:** scrollback ring = `string[]` chunks + byte total capped at `SESSION_SCROLLBACK_REPLAY_BYTES = 256KB` (constants.ts:404); `pendingParse` holds an incomplete OSC tail (≤ `MAX_PENDING_PARSE_BYTES = 4096`).

### Decisive source
```ts
// Titles are emitted on a dedicated `title` event so they travel as a separate
// WebSocket frame. We deliberately do NOT splice OSC sequences into the PTY
// output stream — doing so corrupts in-flight escape sequences from modern
// TUIs (Cursor Agent / Claude Code use DECSET 2026 synchronized output mode
// and any byte landing inside that frame breaks the parser state).  (:17-21)
private appendScrollback(data: string): void {
  this.scrollbackChunks.push(data);
  this.scrollbackBytes += Buffer.byteLength(data, "utf8");
  while (this.scrollbackBytes > SESSION_SCROLLBACK_REPLAY_BYTES &&
         this.scrollbackChunks.length > 1) { /* drop oldest */ }
}
```

**Flow:** spawn (`node-pty`, env from `buildPtyEnvironment`, hooks via `ShellHookBuilder.prepare`) → per data event: intercept DA1/DA2 + DECRQM probes and answer in-process → parse OSC 7/title/alt-screen/foreground/notification/dirty side-channels OUT of-band → emit `output` verbatim → hold an incomplete OSC tail for the next chunk.
**Invariant:** metadata (title/cwd/foreground) travels as control frames, never as bytes inside the output stream; foreground = hook signal ?? alt-screen fallback; attach-time replay is prefixed with live DEC-mode restore so rejoining a TUI re-enters alt screen/mouse even after those sequences scrolled out of the 256KB window.
**Probe:** `packages/server/tests/session.test.ts` :212 "never splices title OSC sequences into PTY output", :278 replay prepends mode-restore prefix, :243 pause/resume suppresses emission.

## Output coordinator — atomic frame vs progressive stream
**Path/Symbol:** `packages/server/src/session-output-coordinator.ts:SessionOutputCoordinator.onSessionOutput` (126–207); `scheduleOutputBatchFlush` (215–235); `maybePauseAfterFlush`/`ensureDrainPoll` (296–336).
**Signature:** `onSessionOutput(managed: ManagedSession, data: string): Promise<void>`.
**Data Shape:** thresholds (constants.ts:324–342): `OUTPUT_BATCH_FLUSH_BYTES=64K`, `OUTPUT_BATCH_WINDOW_MS=2`, `OUTPUT_STREAM_THRESHOLD_MS=100`, `OUTPUT_SYNCHRONIZED_FRAME_TIMEOUT_MS=1000`; water marks: pause ≥4MB / resume ≤1MB / drain poll 50ms / hard backpressure kill at 64MB.

### Decisive source
```ts
if (managed.outputBatch.length >= OUTPUT_BATCH_FLUSH_BYTES) {
  const burstMs = outputAtMs - (managed.outputBurstStartedAtMs ?? outputAtMs);
  if (!managed.outputBurstIsStream && !managed.synchronizedOutputEndDetector.isActive()
      && burstMs >= OUTPUT_STREAM_THRESHOLD_MS) managed.outputBurstIsStream = true;
  if (!managed.outputBurstIsStream) this.openAtomicOutputFrame(managed); // bracket chunks
  this.flushOutput(managed);                       // 64K slices under MAX_OUTPUT_BYTES
  if (managed.outputBurstIsStream) this.closeAtomicOutputFrame(managed);
}
```

**Flow:** accumulate batch → DEC 2026 end ⇒ flush whole batch as one atomic frame immediately → else crossing 64K: classify sustained stream after 100ms, bracket size-split redraws with output-frame-start/end so the browser commits one logical xterm write → small bursts flush on the 2ms idle timer → after every flush, pause the PTY when any client backlog crosses high water until all drain below low water.
**Measured rationale (constants.ts comments):** 180×55 tmux redraws are 182–233 KiB (>1 chunk); 64K chunks parse in 4–6ms under xterm's 12ms write budget (~235 msg/s vs ~470 at 32K — per-message task-lifecycle overhead dominates).
**Probe:** `tests/session-output-coordinator.test.ts` :160 brackets a size-split redraw until its idle boundary, :186 releases a sustained stream after the redraw threshold, :210 keeps a synchronized redraw atomic until DECRST 2026, :92 pauses PTY until renderer backlog drains.

## Transport — per-client framing + 4-mode compression
**Path/Symbol:** `packages/server/src/session-output-transport.ts:sendOutputFrame` (204–247); `makeBrotliEncoder` (45–137); `broadcastBytes` (270–312); header constants constants.ts:347–355.
**Signature:** header byte: `0x00` raw / `0x01` gzip / `0x02` brotli / `0x03` brotli-context-takeover (`0x03` + 4-byte LE raw size, 5-byte header).
**Data Shape:** legacy clients get an untyped stream; framing-enabled always get a type byte. Below `WS_OUTPUT_COMPRESS_THRESHOLD_BYTES = 256` frames stay raw; brotli q=6, gzip level 3 (constants.ts:369–372).

### Decisive source
```ts
// br-ctx: ONE continuous Brotli stream flushed per frame — frame N compresses
// against frames 0..N-1 (prior screen primes the LZ77 window = delta). Flushes
// are chained through a promise FIFO so frames ship in PTY order though each
// BROTLI_OPERATION_FLUSH callback fires on a later tick. (:24-31)
const tail = Promise.resolve();               // per-encoder FIFO
enqueue: tail.then(task); flush: enqueue(() => compress(bytes));
```

**Flow:** pick mode per client → raw/below-threshold ⇒ 0x00 header passthrough → br/gzip sync-compress once per broadcast and share across clients → br-ctx goes through the async encoder queue (raw tails queue behind it).
**Invariant:** compressed and boundary messages never reorder around each other; pending (pre-promote) clients get bounded queues (bytes cap + 256 control messages) and are closed on overflow rather than ballooning.
**Probe:** `tests/session-output-transport.test.ts` :40 orders compressed output/raw tails/boundaries in one FIFO, :84 pixel frames only to framing-enabled clients, :133 raw header for framing-enabled raw-mode clients.

## Kitty graphics scanner — probes answered by the daemon, resets detected across chunk boundaries
**Path/Symbol:** `packages/server/src/kitty-apc-scanner.ts:KittyApcScanner` (83–165); `detectScreenReset` (131–138); `classify` (140–164); coordinator wiring `session-output-coordinator.ts:69-124`.
**Signature:** `push(chunk: string): KittyApcScan { output, frames, probes, screenReset }`; APC = `ESC _ G ... ESC \` (final byte 0x47 'G').
**Data Shape:** `KittyPixelFrame {width,height,imageId,path}` (file medium t=f, f=32 RGBA); `KittyMediumProbe {imageId,quiet,path}` stripped from client output; reset sequences `[ESC[?1049l, ESC[?1047l, ESC[?47l, ESC c]` matched against carried 7-byte tail.

### Decisive source
```ts
private detectScreenReset(buffer: string): boolean {
  const hay = this.resetTail + buffer;              // straddle-safe
  this.resetTail = hay.slice(-SCREEN_RESET_TAIL_BYTES);   // carry 7 bytes
  return SCREEN_RESET_SEQUENCES.some((s) => hay.includes(s));
}
// classify: t!=="f" → other; path must pass isAllowedPath (realpath under the
// daemon's real temp root); a==="q" → probe (STRIPPED, daemon answers it so
// nothing races the emulator's reply); a==="T"/"t" && f===32 → frame relayed.
```

**Flow:** scan each chunk (incomplete APC buffered ≤ `MAX_APC_BUFFER_BYTES = 64KB`) → probes: daemon stats the realpath'd file and writes `\x1b_Gi=<id>;OK|ENOENT\...` into the PTY — only when EVERY attached viewer has binary framing (else leave unanswered, app falls back inline) → frames relayed as 0x04 binary WS messages → screenReset after prior frames ⇒ cancel in-flight relay + broadcast `pixel-frames-clear`.
**Probe:** `tests/kitty-apc-scanner.test.ts` :42 probe detected+stripped, :53 transmit split across data events reassembles, :64 outside-temp-root ignored; `tests/kitty-screen-reset.test.ts` :29 leave split across chunks, :106 pixel-frames-clear only for apps that framed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "SessionOutputCoordinator|SessionOutputTransport|makeBrotliEncoder|KittyApcScanner|^Session$|buildPtyEnvironment", limit: 10 });
```
Graph check this session: KittyApcScanner 83–165, SessionOutputCoordinator 34–354, buildPtyEnvironment 25–88 resolved line-exact vs HEAD.

## Verdict
Adopt out-of-band metadata channels (never splice OSC into output), water-mark flow control instead of socket kills, the atomic-frame/stream classifier with DEC 2026 authority + safety timeout, per-frame typed-header compression with a chained-FIFO context-takeover encoder, daemon-side kitty probe answering with temp-root allow-listing, and straddle-safe screen-reset detection; adapt threshold values, client handshake fields, and shell/platform specifics to host; omit the React browser app and capture/hibernate renderers unless porting the full product. Tests run under vite-plus; probes cited from on-disk test files.
