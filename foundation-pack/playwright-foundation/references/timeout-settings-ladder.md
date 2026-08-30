<!-- capsule-v2 -->
# TimeoutSettings precedence ladder — which timeout wins between option, default, debug mode, and parent?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** When a user passes no timeout, where does the effective timeout come from — and why do navigation and launch resolve differently from plain actions?

## Three ladders over a parent chain
**Path/Symbol:** `packages/playwright-core/src/client/timeoutSettings.ts:TimeoutSettings` (`_timeout` 79-89, `_navigationTimeout` 65-77, `_launchTimeout` 91-99) + `kNoTimeout` (26).
**Signature:** `timeout(options: { timeout?: number, signal?: AbortSignal }): TimeoutOptions`; same for `navigationTimeout`/`launchTimeout`; `kNoTimeout: { signal: undefined, timeout: 0 }`.
**Data Shape:** defaults are `number | undefined` per level; parent is another TimeoutSettings (context → browser chain); constants in `packages/isomorphic/time.ts`: `DEFAULT_PLAYWRIGHT_TIMEOUT = 30_000`, `DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT = 3 * 60 * 1000`.

### Decisive source
```ts
private _navigationTimeout(options: { timeout?: number }): number {
    if (typeof options.timeout === 'number')
      return options.timeout;
    if (this._defaultNavigationTimeout !== undefined)
      return this._defaultNavigationTimeout;
    if (debugMode() === 'inspector')
      return 0;                       // inspector mode = wait forever
    if (this._defaultTimeout !== undefined)
      return this._defaultTimeout;
    if (this._parent)
      return this._parent._navigationTimeout(options);
    return DEFAULT_PLAYWRIGHT_TIMEOUT;   // 30s
}

private _launchTimeout(options: { timeout?: number }): number {
    if (typeof options.timeout === 'number')
      return options.timeout;
    if (debugMode() === 'inspector')
      return 0;
    if (this._parent)
      return this._parent._launchTimeout(options);
    return DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT;   // 3min
}
```

**Flow:** explicit numeric option always wins (`typeof === 'number'`, so `timeout: 0` means "no timeout" legitimately); then the method-specific default (navigation only); then inspector debug-mode → 0 (never time out while debugging); navigation additionally honors the generic default before delegating; finally walk the parent chain. Plain `_timeout` ladder: option → generic default → inspector → parent → 30s. Launch skips BOTH local defaults (a context's setDefaultTimeout must not shrink browser launch) ending at 3 minutes.
**Invariant:** `kNoTimeout ({ timeout: 0 })` marks internal calls that intentionally opt out of deadlines — internal plumbing uses it instead of relying on unset defaults; `timeout: 0` as user input disables the deadline rather than falling through to defaults (number-check, not truthiness). Signal passes through untouched on every rung.
**Probe:** `grep -c "debugMode() === 'inspector'" packages/playwright-core/src/client/timeoutSettings.ts` → `3` (one per ladder); `grep -c "_parent._timeout(options)" packages/playwright-core/src/client/timeoutSettings.ts` → `1`; `grep -n "kNoTimeout" packages/playwright-core/src/client/timeoutSettings.ts` → line 26; `grep -c "export const DEFAULT_PLAYWRIGHT_TIMEOUT = 30_000" packages/isomorphic/time.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "navigationTimeout", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: `client.timeoutSettings.TimeoutSettings.navigationTimeout ... timeoutSettings.ts 53-55` + `_navigationTimeout 65-77`.)

## Verdict
Adopt the ordered ladder with number-typed zero-means-infinite semantics, the navigation-specific rung, the launch-path isolation, and inspector-mode infinite waits. Adapt constants and debug-mode detection to your host. Omit the signal pass-through only if your API has no cancellation story. Direct behavior pinned by `tests/library/multiclient.spec.ts` ("should have separate default timeouts", line 110 — asserts distinct 500ms/600ms Timeout messages across two pages sharing one browser), proving per-context settings don't leak across the parent chain's siblings.
