<!-- capsule-v2 -->
# pageInfo modal probe — how do you ask a page for state when a native dialog may have frozen its JS?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What should an eval-based health check return instead of silently hanging on `alert()`/`confirm()`?

## Timed eval race, exception surfacing, dialog-vs-unresponsive verdict split
**Path/Symbol:** `skills/cdp/sdk/helpers.ts:pageInfo` (:193-211); reads `_lastDialog` set by the signal handler (agent-signals-digest capsule).
**Signature:** `pageInfo(opts?: { timeoutMs?: number }): Promise<Record<string, unknown>>` — default timeout 2000ms.
**Data Shape:** success `{url,title,w,h,sx,sy,pw,ph}` (JSON.stringify'd in-page, parsed node-side) · blocked `{dialog:{type,message,defaultPrompt}}` · hung-no-dialog `{unresponsive:true,hint}`.

### Decisive source
```ts
const evalP = session.domains.Runtime.evaluate({ expression: EXPR, returnByValue: true });
const timeoutP = new Promise<never>((_, rej) => setTimeout(() => rej(new Error('pageInfo timeout after ' + timeoutMs + 'ms')), timeoutMs));
try {
  const result = await Promise.race([evalP, timeoutP]);
  if (result && result.exceptionDetails) throw new Error(e.text ?? e.exception?.description ?? 'Runtime.evaluate exception');
  if (result && result.result && result.result.value) return JSON.parse(result.result.value);
  return {};
} catch {
  if (_lastDialog) return { dialog: _lastDialog };
  return { unresponsive: true, hint: 'Page JS did not respond in time. Likely a blocking modal dialog, ...' };
}
```

**Flow:** race the eval against a node-side timer → clean result → parse and return → on ANY failure path consult `_lastDialog`: a known open dialog means "the page didn't hang, it's blocked" (`{dialog}`), otherwise report `{unresponsive}` with a hint naming likely causes (modal, long sync task, mid-navigation).
**Invariant:** (1) CDP calls have NO built-in timeout — every page-side eval that might stall MUST be raced node-side or it hangs forever; this helper is the repo's canonical instance of that rule. (2) The dialog/unresponsive distinction matters because the remedies differ: dismiss via `Page.handleJavaScriptDialog` vs retry/wait. (3) The in-page expression stringifies once and returns a single small object — never pipe big values through this path.
**Probe:** no direct test. Deterministic probe: `grep -n "_lastDialog\|Promise.race" skills/cdp/sdk/helpers.ts` (:139/:208, :200); behavior contract documented in `interaction-skills/agent-operating-loop.md` anti-patterns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "pageInfo", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the race-plus-verdict-split for any LLM-facing eval bridge; adapt the 2s default and hint text to your stack; omit nothing — dropping the dialog branch reintroduces exactly the silent hang the helper exists to kill.
