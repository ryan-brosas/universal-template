<!-- capsule-v2 -->
# MSW contract-fixture mock fleet — how does a browser mock double as an executable conformance test of a published contract?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How do you wire an MSW worker so it ships zero bytes in production, installs before any query fires, and stays byte-faithful to an external API contract instead of drifting?

## Gated dynamic worker + fixture-driven handlers
**Path/Symbol:** `src/entry.client.tsx:17-33` (`prepareApp`), `src/mocks/should-start-mock-worker.ts:1-9`, `src/mocks/browser.ts` (4 L), `src/mocks/automation-handlers.ts` (:21–49, :54–101).
**Signature:** `shouldStartMockWorker({ mockApi = import.meta.env.VITE_MOCK_API, hasWindow = typeof window !== "undefined" } = {}): boolean`; `export const worker = setupWorker(...handlers)`.
**Data Shape:** Gate = `hasWindow && mockApi === "true"` (strict string equality — `"1"` does NOT enable). Handlers answer from `capabilitiesFixture.responses.supported.body` imported out of the published `@openhands/extensions/testing/automations/capabilities.json`.

### Decisive source
```ts
async function prepareApp() {
  await waitForI18n();
  if (shouldStartMockWorker()) {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass" });
  }
  // …
}
prepareApp().then(() => startTransition(() => { hydrateRoot(…) }));
```
```ts
// The schedules the mock can read: "* * * * *" and "*/N * * * *". Anything
// else is assumed to satisfy the deployment minimum — this stands in for the
// service's cron parser rather than reimplementing it.
const STEP_SCHEDULE_PATTERN = /^(?:\*|\*\/(\d+)) \* \* \* \*$/;
```

**Flow:** app boot → gate check → dynamic import (tree-shakes the whole fleet from prod bundles) → `worker.start` resolves BEFORE `hydrateRoot` → no query can ever race the mock install. Handlers keep a per-session mutable `Map` reset by `resetAutomationMockData()`; every handler `delay(100–300)`s and `request.clone()`s before body reads.
**Invariant:** The mock must reproduce exactly the checks the published fixtures record — no more, no less. `validateDraftTrigger` implements only cron-interval-below-minimum and event-type-not-delivered (errors addressed by dotted path, e.g. `trigger.schedule` / `trigger.on`); `REGISTERED_EVENT_TYPES` deliberately excludes one SUPPORTED type so the fixtures' not-delivered scenario stays reachable; unmodelable schedule shapes (`"0 0 31 2 *"`) pass validation because only the real service may reject them.
**Probe:** `__tests__/api/automation-handlers.test.ts:89-107` — `it.each(PREFLIGHT_EXCHANGES)` replays EVERY preflight exchange recorded in the published fixtures and asserts `{status, body}` equality; executed deterministic probe of the gate under node strip-types: `"true"`+window→true, `"1"`→false, no-window→false (porting caveat observed live: omitting args outside Vite crashes on `import.meta.env.VITE_MOCK_API` because plain Node has no `import.meta.env`).

### Wiring details worth porting
- `onUnhandledRequest: "bypass"` (app entry) vs `"error"` (the handler unit-test server, `setupServer(...AUTOMATION_HANDLERS)` listen) — permissive at runtime, strict in tests.
- Unit tests drive handlers through plain `fetch("/api/automation/v1?…")` with `msw/node`, so the same handler array serves browser dev, node tests, and contract replay.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "mock service worker handlers setup reset", limit: 10, fields: ["lines"] });
// → shouldStartMockWorker :1-9, resetAutomationMockData :96-101, msw-websocket-setup helpers
```

## Verdict
Adopt the gate/dynamic-import/pre-hydration ordering and the fixture-replay conformance pattern. Adapt the env-var name and fixture source to your contract publisher. Omit the OpenHands automation domain fixtures themselves. Coverage caveat: none recorded at pin; vitest runner blocked in inspo tree so the it.each replay is read-at-HEAD evidence.
