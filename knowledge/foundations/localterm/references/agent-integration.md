<!-- capsule-v2 -->
# Agent integration — how does an in-agent extension upgrade terminal capabilities, notify humans, and take over the bash tool?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What are the timing/consent rules for an extension that changes pi-tui capabilities, sends OSC 9 notifications, and replaces the bash tool with a scrubbed+redacted one?

## Kitty images — set capabilities BEFORE the first capability query
**Path/Symbol:** `packages/pi-extension/extensions/kitty-images.ts:enableKittyImages` (10–14).
**Signature:** `enableKittyImages(): void` — synchronous, called while the extension factory loads.
**Data Shape:** `getCapabilities()` / `setCapabilities({...caps, images: "kitty", hyperlinks: true})` from `@earendil-works/pi-tui`; idempotent (returns early when already enabled).

### Decisive source
```ts
// Enable them while the extension factory is loading, before TUI.start()
// checks image support and sends its CSI 16 t cell-metrics query. Waiting for
// session_start is too late: the first query is then skipped and image sizing
// keeps pi-tui's fallback cell dimensions.  (:6-9)
```

**Flow:** localterm's browser renders kitty graphics + OSC 8 via xterm addons but advertises plain `TERM=xterm-256color` (identity vars stripped — see architecture.md), so pi-tui reports images unsupported → the extension flips capability flags at load time → TUI.start() then queries and sizes correctly.
**Invariant:** capability flags must be set before the first capability query, not on session_start.
**Probe:** `packages/pi-extension/tests/kitty-images.test.ts` :18 enables synchronously, :50 does not rewrite already-enabled capabilities.

## Agent notifications — settle-gated, elapsed-gated, sanitized OSC 9
**Path/Symbol:** `packages/pi-extension/extensions/agent-notify.ts:registerAgentNotify` (16–85); `src/utils/agent-notify-body.ts:extractAssistantExcerpt/formatAgentEndBody` (34–47 / 57–67); `src/utils/osc-sequence.ts:buildOsc9Sequence` (25–33); `constants.ts:AGENT_NOTIFY_MIN_ELAPSED_MS=30_000, AGENT_NOTIFY_EXCERPT_MAX_CHARS=160, NOTIFICATION_MAX_LENGTH=1024` (49/61/44).
**Signature:** `buildOsc9Sequence(body, maxLength = 1024): string`; `extractAssistantExcerpt(messages): string | undefined`.
**Data Shape:** notification fires only on `agent_settled` AND no in-flight retry AND elapsed ≥ 30s AND mode === "tui"; body = `pi finished: <session> — <excerpt> (<elapsed>)`.

### Decisive source
```ts
// osc-sequence.ts — a BEL would terminate the OSC early; ESC could forge an ST:
const sanitized = Array.from(body, (c) => (isControlOrDel(c) ? " " : c)).join("");
// code-point loop (not a control-char regex) keeps eslint no-control-regex clean
// and astral chars unsplit; cap BEFORE framing so the daemon's own 1024-unit
// slice can never split a surrogate pair. (:7-24)
// agent-notify.ts — retry correlation:
pi.on("agent_settled", (_e, ctx) => { hasCurrentRunSettled = true; settledContext = ctx;
  if (activeRetryId === undefined) emitNotification(); });   // wait for retry completion first
```

**Flow:** agent_start stamps turn start → agent_end captures messages → retry started/completed/cancelled events gate emission (cancelled resets without notifying) → emitNotification checks all gates, formats, writes OSC 9 to stdout.
**Invariant:** never notify mid-retry or on quick turns; excerpt = last assistant TEXT blocks only (thinking/tool calls skipped), whitespace-collapsed, ellipsis-capped; control chars replaced by spaces before framing.
**Probe:** `tests/agent-notify.test.ts` :69 emits only after agent_settled, :81 waits for pi-retry completion after the final run settles, :116 cancelled retry ⇒ no emit; `tests/osc-sequence.test.ts` :9 control chars replaced, :17 capped to maxLength.

## Bash tool reconstruction — override carries settings through (see secret-defense.md for the defense)
**Path/Symbol:** `packages/pi-extension/extensions/bash-secret-scrub.ts:registerBashSecretScrub` (69–94).
**Signature:** `pi.registerTool(createBashToolDefinition(cwd, { operations, spawnHook, commandPrefix, shellPath }))`.
**Data Shape:** reads `readPiShellSettings(cwd)` once at registration (global + project `.pi/settings.json`, project wins); strip set + redaction values recomputed on every `session_start`.

**Invariant:** overriding a built-in tool BY NAME means the replacement must re-bake everything the original did — here shellPath + shellCommandPrefix or the user's config silently vanishes.
**Probe:** `tests/read-pi-shell-settings.test.ts` :36/:48 project-override and global-fallback behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "enableKittyImages|registerAgentNotify|buildOsc9Sequence|extractAssistantExcerpt|readPiShellSettings", limit: 8 });
```
Graph check this session: enableKittyImages resolved at kitty-images.ts 10–14, line-exact vs HEAD.

## Verdict
Adopt load-time capability setting (before first query), the four-gate notification ladder (settled + not-retrying + ≥30s + tui-mode), code-point-safe OSC sanitization with pre-frame capping, backward-scanning text-only excerpts, and settings passthrough on tool override; adapt the extension API surface (`pi.on`, `pi.events`, registerTool), thresholds, and OSC codes to your host; omit pi-specific session/retry event names unless targeting pi. Probes cited from on-disk test files (vite-plus).
