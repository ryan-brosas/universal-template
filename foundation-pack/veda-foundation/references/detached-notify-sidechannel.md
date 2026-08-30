<!-- capsule-v2 -->
# macOS notify side-channel — fire-and-forget detached osascript that can never block the pipeline

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I add desktop notifications to a long CLI run without adding a failure mode or slowing exit?

## Platform-gated spawn().unref() notification + sound resolution ladder
**Path/Symbol:** `src/util/notify.ts:notify` (:69–101); helpers `truncate` (:22–25), `formatBackendModel` (:37–44), `resolveNotifySoundPath` (:46–63).
**Signature:** `function notify(options: NotifyOptions): void` — synchronous, non-blocking, no promise.
**Data Shape:** Sound spec resolves: empty→default `Purr.aiff`; `none|off|silent`→null (no afplay); contains `/`→verbatim path; bare name→`/System/Library/Sounds/<name>[.aiff]`.

### Decisive source
```ts
export function notify(options: NotifyOptions): void {
  if (process.platform !== 'darwin') return;   // fails gracefully on non-macOS
  ...
  spawn('osascript', ['-e', script], { detached: true, stdio: 'ignore' }).unref();
  if (soundPath) {
    spawn('afplay', [soundPath], { detached: true, stdio: 'ignore' }).unref();
  }
}
```

**Flow:** platform gate returns early elsewhere → title suffixed with display name (`Codex GPT-5.2` via BACKEND_DISPLAY_NAMES map, fallback raw backend id) → double-quote escaping only (`"` → `\"`) into an osascript `-e` string → both child processes detached+unref'd so the parent never waits.
**Invariant:** Notifications are strictly best-effort: no await, no error surface, no exit-code coupling — a missing binary or failed sound cannot affect run outcome. `stdio: 'ignore'` prevents pipe-buffer backpressure from ever stalling the parent. Non-macOS is a silent no-op, not an error.
**Probe:** No dedicated upstream test file exists for this module (verified against tests/util inventory). Coverage caveat recorded honestly; deterministic check pins the platform gate + unref pattern above byte-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "notify NotifyOptions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the detached-unref best-effort pattern for ANY cosmetic side channel (notifications, sounds, telemetry pings). Adapt display-name map and sound defaults. Omit entirely on non-macOS hosts — the gate IS the portability contract.
