<!-- capsule-v2 -->
# Serialized two-step closeTab — why does Target.closeTarget alone leave ghost tabs, and what ordering fixes it?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What close sequence actually removes the tab from the browser window across Chromium forks?

## window.close() → 100ms delay → CDP teardown, all on one promise queue
**Path/Symbol:** `skills/cdp/sdk/session.ts:Session.closeTab` (:225-258).
**Signature:** `closeTab(targetId: string, sessionId?: string): Promise<void>` — returns the tail of the shared `closeQueue`, so callers may fire-and-forget with `.catch(() => {})`.
**Data Shape:** best-effort at every step (each sub-call individually try/caught); the method itself never rejects except through queue mechanics.

### Decisive source
```ts
const doClose = async () => {
  if (sessionId) {
    try { await this._call('Runtime.evaluate', { expression: 'window.close()' }, { sessionId }); }
    catch { /* session may already be detaching */ }
    await new Promise(r => setTimeout(r, 100));
  }
  try { await this.domains.Target.closeTarget({ targetId }); }
  catch { /* already gone */ }
};
// Serialize: each close waits for the previous one to finish.
this.closeQueue = this.closeQueue.then(doClose, doClose);
return this.closeQueue;
```

**Flow:** enqueue on the persistent per-Session queue → `window.close()` inside the tab (triggers the browser's own tab-strip removal path; works for every tab opened via `Target.createTarget`) → fixed 100ms settle so the UI close lands before CDP teardown → `Target.closeTarget` detaches the CDP side.
**Invariant:** (1) ORDER IS LOAD-BEARING: some Chromium forks (Dia, Arc) honor `Target.closeTarget` at the protocol level but never remove the tab from the visible window — only `window.close()` walks the browser's real close path. (2) Closes must be SERIALIZED: interleaved closes can tear a session down before another tab's `window.close()` takes effect. `.then(doClose, doClose)` keeps the queue alive even when a link rejects. (3) The 100ms delay lives between the steps, not after the whole operation.
**Probe:** no direct test (needs a live browser). Deterministic probe: `grep -n "closeQueue\|window.close()" skills/cdp/sdk/session.ts` pins the queue (:256) and the ordering (:247-252).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "closeTab", limit: 3, fields: ["signature", "name", "file"] });
// resolves Session.closeTab @ session.ts:243-258
```

## Verdict
Adopt the window-close-first + serialized ladder verbatim in any CDP automation that creates and disposes tabs; adapt the 100ms constant upward if you observe slower forks; omit the `Runtime.evaluate` step only when you never created the target yourself (script-opened windows are the case it covers). Coverage caveat: behavior confirmed from the source comment + code; upstream has no headless test for visual tab-strip state.
