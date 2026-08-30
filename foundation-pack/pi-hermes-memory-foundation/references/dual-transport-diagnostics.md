<!-- capsule-v2 -->
# Both-transports failure diagnostics — a background LLM task that can fail twice must report ONE actionable warning after both paths settle

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** Direct completion failed silently and you fell back to the subprocess — if the subprocess ALSO fails, what does the user actually see?

## runReview dual-failure reporting
**Path/Symbol:** `src/handlers/background-review.ts:runReview` (:225–283) — `directFailure` capture at :226/:243–251 (fallbackReason + error joined, or thrown error stringified), subprocess throw path :255–266, non-zero-exit-with-directFailure path :270–277; helper `diagnosticDetail` (:111–113, `Error.message || String(value).trim()`, whitespace-collapsed, `.slice(0, 300)`).
**Signature:** `runSubprocessReview(pi, prompt, config, execChild, ctx: Pick<ExtensionContext, "cwd" | "model" | "signal">): Promise<{ code; stdout?; stderr? }>`.
**Data Shape:** one `ctx.ui.notify(msg, "warning")` per review cycle carrying BOTH halves: `"Memory auto-review failed in both transports. Direct: ${detail}. Subprocess: ${detail}. Check the active model/provider or set llmModelOverride."`

### Decisive source
```ts
let subprocessResult;
try { subprocessResult = await runSubprocessReview(pi, subprocessPrompt, config, execChild, ctx); }
catch (error) {
  if (directFailure) {          // only warn when BOTH paths are dead
    ctx.ui.notify(`Memory auto-review failed in both transports. `
      + `Direct: ${diagnosticDetail(directFailure)}. Subprocess: ${diagnosticDetail(error)}. `
      + `Check the active model/provider or set llmModelOverride.`, "warning");
  }
  return;                        // direct-only failure stays silent (fallback ran)
}
if (subprocessResult.code === 0) { notifyIfSaved(…); }
else if (directFailure) {        // exit≠0 with a prior direct failure ⇒ same warning,
  const subprocessDetail = subprocessResult.stderr?.trim() || subprocessResult.stdout?.trim()
    || `exit code ${subprocessResult.code}`;
  ctx.ui.notify(…both transports…, "warning");
}                                // exit≠0 WITHOUT direct failure = old silent contract
```

**Flow:** direct transport attempt → any failure (thrown OR `{ok:false}` beyond the silent `empty`/handled fallback reasons) recorded as `directFailure`, never surfaced alone → subprocess runs → success ⇒ save notification as usual → subprocess throw or non-zero exit WITH a stored directFailure ⇒ exactly one warning naming root causes of both legs plus the fix knob (`llmModelOverride`).
**Invariant:** a single-path failure must stay quiet (the ladder exists precisely so one leg dying is unremarkable), but a DOUBLE failure must never be invisible — the old code swallowed it (`catch {}`). The message is diagnostic-first: each half is capped at 300 chars of flattened detail, and the remedy hint names the config key. `runReview()`'s outer `.catch(() => {})` remains as last-resort teardown protection only.
**Probe:** `npx tsx --test tests/handlers/background-review.test.ts` — "surfaces one actionable diagnostic when direct and subprocess review both fail" (:803, mock direct returns `no_auth` + error, mock exec exits 1 with stderr `No API key for local-llama/local-9b`; asserts EXACTLY ONE warning matching `/both transports/i`, `/no_auth/i`, `/No API key for local-llama\/local-9b/i`, `/llmModelOverride/i`) and the silent-single-failure controls ("does NOT crash agent when exec throws" :515, empty-direct no-fallback :860). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "runSubprocessReview diagnosticDetail shouldNotifySubprocess", limit: 5 })`

## Verdict
Adopt fail-loudly-only-on-total-failure for any best-effort background pipeline with a fallback. Adapt the notify channel and remedy hint. Pair with `background-review-loop.md` (the trigger/threshold machinery around this) and `review-model-auth-resolution.md` (the most common failure cause).
