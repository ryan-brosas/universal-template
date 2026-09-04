<!-- capsule-v2 -->
# ACP smoke harness — how do you end-to-end test a stdio protocol adapter without an IDE or a client?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you drive the REAL adapter binary over stdio NDJSON, assert semantic outcomes (not just "got a response"), and never touch the user's real agent store?

## SmokeHarness + isolated agent overlay
**Path/Symbol:** `scripts/lib/acp-smoke.mjs` whole (301L) — `createIsolatedAgentEnv` (:29-58), `SmokeError` (:61-72), `assert`/:74, `matches`/:78, `SmokeHarness` (:82-301: constructor :83-111, `distHash` :113-115, `start` :117-144, `_onData` :146-161, `_onMessage` :163-177, `request` :179-197, `notify` :200-204, `expectResult` :207-210, `expectError` :213-230, `waitForUpdate` :232-254, `updateTexts` :256-258, `close` :260-279, `removeIsolation` :281-285, `assertExited` :287-292, `_failAll` :294-300). Constants: `DEFAULT_REQUEST_TIMEOUT_MS=30_000`, `DEFAULT_DEADLINE_MS=120_000`, `GRACE_MS=5_000`, `ISOLATE_TEMP_DIRS=['sessions','cache','fabric']`. Scenario scripts: `scripts/smoke-{startupinfo,acp,acp-load,session,modes,queue,changelog,export,compact,cancel,lifecycle,negative,mcp-fixture,ide-inspect,gaps}.mjs`; runner matrix in `package.json` (`smoke:full` chains all 15).
**Signature:** `new SmokeHarness({ dist='dist/index.js', cwd, env={}, deadlineMs, requestTimeoutMs, isolate=true }).start()`; `request(id, method, params, {timeoutMs})`.
**Data Shape:** pending = `Map<id, {resolve,reject,timer,method}>`; updates[] collects `session/update.params.update`; stderr[] retains raw lines; `SmokeError` exposes `{code, messageText, details}` from the JSON-RPC error envelope.

### Decisive source
```js
// F-027: symlink the real pi config so provider auth/models keep working, keep
// sessions/cache/fabric in a temp dir, and point the adapter session map at the same temp dir.
const ISOLATE_TEMP_DIRS = ['sessions', 'cache', 'fabric']
function createIsolatedAgentEnv() {
  const real = resolve(process.env.HOME ?? '', '.pi', 'agent')
  const base = mkdtempSync(join(tmpdir(), 'pi-acp-smoke-'))
  for (const name of readdirSync(real)) {           // best-effort per-entry symlinks
    if (ISOLATE_TEMP_DIRS.includes(name)) continue
    try { symlinkSync(join(real, name), join(base, name)) } catch { /* non-fatal */ }
  }
  for (const dir of ISOLATE_TEMP_DIRS) mkdirSync(join(base, dir), { recursive: true })
  return { env: { PI_CODING_AGENT_DIR: base,
                  PI_ACP_SESSION_MAP: join(base, 'pi-acp-session-map.json') },
           cleanup: () => rmSync(base, { recursive: true, force: true }) }
}
```
```js
_onMessage(msg) {
  if (msg?.id !== undefined) {                 // response: settle exactly one pending
    const entry = this.pending.get(msg.id)
    if (entry) { this.pending.delete(msg.id); clearTimeout(entry.timer)
      if (msg.error) entry.reject(new SmokeError(msg, entry)); else entry.resolve(msg) }
    return
  }
  if (msg?.method === 'session/update') this.updates.push(msg.params?.update ?? msg.params ?? msg)
}
async close({ graceMs = GRACE_MS } = {}) {     // SIGTERM -> grace race -> SIGKILL
  child.kill('SIGTERM')
  const winner = await Promise.race([exited, new Promise(r => setTimeout(() => r('timeout'), graceMs))])
  if (winner === 'timeout') { child.kill('SIGKILL'); await exited }
}
```

**Flow:** harness start → optional isolated agent-dir overlay via env (`PI_CODING_AGENT_DIR` + `PI_ACP_SESSION_MAP`) → spawn `node dist/index.js` with piped stdio → newline-buffered JSON parse (bad lines skipped) → id-keyed correlation with per-request timers; notifications filtered to session/update collection → scenario script asserts with `expectResult`/`expectError(code, messagePattern)`/`waitForUpdate(predicate)` → close ladder SIGTERM→SIGKILL → `assertExited(0)`; FAIL path prints the last 20 stderr lines. A whole-harness deadline timer rejects every pending request so nothing hangs.
**Invariant:** Scripts assert SEMANTIC outcomes ("result vs error envelope", exact codes/patterns) instead of treating any response id as success; the user's real `~/.pi/agent` sessions/cache are never written (only symlinked config entries are shared); every run stamps its dist provenance via `distHash()`.
**Probe:** `node scripts/smoke-session.mjs` — EXECUTED GREEN this pass: `OK smoke-session (dist 3d5ffcd2e2d8; stats text 1602 chars)` against pin HEAD build (real child adapter + real pi RPC subprocess, no model call needed for the /session builtin). Runner matrix: `npm run smoke:full`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", qn_pattern: "^pi-acp\\.scripts\\.lib\\..*", limit: 20 });
// -> SmokeHarness Class 82-301 (15 fan-in), createIsolatedAgentEnv 29-58, SmokeError 61-72, assert/matches ...
```

## Verdict
Adopt the whole rig for any stdio/JSON-RPC agent adapter: env-based store isolation overlay, id-correlated request harness with deadline fan-out, typed error assertions, predicate-poll update waiting, and SIGTERM→SIGKILL close with exit-code assertion. Adapt the overlay paths and the notification filter to your protocol. Omit nothing — the file is self-contained. Coverage caveat: smoke scripts require `npm run build` + an installed agent binary; unit-test fleet does not cover this file (probes are the smoke runs themselves).
