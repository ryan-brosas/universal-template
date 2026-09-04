<!-- capsule-v2 -->
# Footer status dedupe — how do you render a live usage line on a timer without churning the host UI?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** A footer/status line refreshed on a 500ms tick must reflect cumulative delegate usage exactly once per change — what is the render-and-dedupe contract, and what happens at init/dispose?

## Text-diff setStatus with sticky-empty latch
**Path/Symbol:** `src/footer-status.ts` whole file (51L): format ladder :9-15 (`formatCompactTokens`), init :17-20 (`initFooterStatus`), tick :24-39 (`updateFooterStatus`, the seam), teardown :41-50 (`disposeFooterStatus`); driver at `src/fleet-widget.ts`:63-99 (`refresh()` calls it on empty-list final render :75 AND every active tick :98; `REFRESH_MS = 500` at :5).
**Signature:** `formatCompactTokens(count: number): string`; `initFooterStatus(ctx: ExtensionContext): void`; `updateFooterStatus(): void`; `disposeFooterStatus(): void`.
**Data Shape:** module-level `ui` handle + `lastFooterText: string | undefined` — initialized to `undefined` by init (forces first render) and to `""` by dispose (sticky-empty). Usage comes from `getDelegateUsage()` (delegate-tool accumulator): `{ input, output, totalTokens, cost: { total } } | undefined`. Rendered line: `` `sub-agents ↑12k ↓31 ($0.0016)` `` (lowercase k/M arrows are literal `\u2191\u2193`).

### Decisive source
```ts
// src/footer-status.ts:24-39 — dedupe is the WHOLE point of the tick:
export function updateFooterStatus(): void {
  if (!ui) return;
  const usage = getDelegateUsage();
  let text: string | undefined;
  if (usage && usage.totalTokens > 0) {
    const costStr = usage.cost.total > 0 ? ` ($${usage.cost.total.toFixed(4)})` : "";
    text = `sub-agents \u2191${formatCompactTokens(usage.input)} \u2193${formatCompactTokens(usage.output)}${costStr}`;
  }
  if ((text ?? "") === lastFooterText) return;   // ← unchanged text NEVER re-sets
  lastFooterText = text ?? "";
  try { ui.setStatus(FOOTER_STATUS_KEY, text); } catch { /* session tearing down */ }
}
```

**Flow:** init binds ui + resets lastFooterText to undefined → each 500ms refresh computes the desired text from cumulative usage → compare against lastFooterText with `(text ?? "") === lastFooterText`: equal ⇒ return WITHOUT calling setStatus (covers both "same numbers" and repeated EMPTY ticks) → changed ⇒ store then `setStatus(key, text)` in try/catch → dispose clears via `setStatus(key, undefined)` (also try/catch), detaches ui, sets lastFooterText = "" so a post-dispose tick is a no-op double-guard.
**Invariant:** (1) Zero-total and no-usage must RENDER AS CLEAR (`text` stays `undefined` → `setStatus(key, undefined)`), not as a literal "0" line — pinned twice (tests :60-67 no usage, :69-77 totalTokens=0). (2) The empty state participates in dedupe: repeated empty ticks call setStatus exactly ONCE ("does not churn setStatus across repeated empty ticks", tests :90-105 asserts calls.length===1 then ===2 after usage arrives). This requires normalizing undefined→"" on BOTH sides of the comparison. (3) Format ladder mirrors pi's own footer.js EXACTLY (comment :8): lowercase k/M, boundaries <1000/<10000/<1e6/<1e7 — test pins all four boundaries incl. 999999→"1000k" quirk and 9999999→"10.0M". Porters changing the ladder break visual parity with host footers. (4) Cost shown only when >0, 4-decimal fixed. (5) Every host call is best-effort try/catch — a tearing-down session must never crash the tick.
**Probe:** `cd $REFERENCE_ROOT/coding-agents/billion-context-pi && node_modules/.bin/tsx --test tests/footer-status.test.ts` → 6 pass / 0 fail executed GREEN at pin (dedupe-once, clear-on-zero ×2, dispose detach, boundary ladder, churn guard).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "updateFooterStatus setStatus delegate usage dedupe", limit: 10 });
```

## Verdict
Adopt: timer-driven status lines must diff rendered TEXT before touching the host API, treat the cleared state as a first-class value in that diff, and wrap every host mutation in best-effort catch. Adapt the key name, format ladder, and usage source to your host. Omit nothing from the latch lifecycle — skipping the init-reset or the dispose "" assignment reintroduces either a missed first render or post-dispose churn.
