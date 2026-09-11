<!-- capsule-v2 -->
# Error Funnel & Reporting — how do you turn random extension crashes into deduplicated, feature-attributed, one-click-reproducible reports?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the pipeline from a thrown error to a console group with pre-filled issue links?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/errors.ts:` `catchErrors` (:88–107), `logError` (:34–86), `parseFeatureNameFromStack` (:20–29), `disableErrorLogging` (:8–10).
**Signature:** `logError(error: Error): void`; `catchErrors(): void` (installs global handlers); `parseFeatureNameFromStack(stack?): FeatureId | undefined`.
**Data Shape:** dedupe key = raw `error.stack` in a `Set`. Attribution = LAST stack frame matching `/assets\/features\/(?<id>.+)\.js/`.

### Decisive source
```ts
// The stack may show other features due to cross-feature imports, but we want
// the top-most caller so we need to REVERSE it:
const match = stack.split('\n').toReversed().join('\\n').match(/assets\/features\/(?<id>.+)\.js/);
```
```ts
// unhandledrejection: only claim errors that clearly belong to the extension,
// or every page script's failures would be swallowed:
if (error?.stack.includes('-extension://') || error?.stack.includes('webkit-masked-url://')) {
	logError(error);
	event.preventDefault();
}
```

**Flow:** `globalThis 'error'` → any Error object → logError; `'unhandledrejection'` → ownership filter by stack marker → logError → short-circuits: logging disabled (logged-out pages), "Extension context invalidated" (update/reload notice, warn-once via memoized console.warn), duplicate stack → then attribution → token-related messages downgraded to ℹ️ info logs (with fine-grained-token copy rewritten) → everything else renders a `console.group('❌ Refined GitHub: <id|global>')` containing version+GHE badge, the error, and PRE-BUILT search/new-issue URLs (`title=\`${id}\`: ${message}`, `repro=location.href`, `description=stack in fences`).
**Invariant:** attribution scans the REVERSED stack because the innermost frames are library code — matching forward would attribute to whichever feature imported a helper first. The unhandledrejection handler must filter by extension-owned stack markers or it hijacks the host site's errors. `console.group`/single-parameter logs are deliberate for Safari (which formats multi-arg poorly) — porters collapsing them back to `console.error(err)` lose Safari reporting entirely.
**Probe:** no direct unit test; deterministic pins: reversed-stack regex at :22–28, ownership filter strings at :102, group format at :81–85. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "logError catchErrors parseFeatureNameFromStack", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the funnel shape (dedupe-by-stack, reverse-scan attribution, ownership-filtered rejection handler, report-link synthesis) for any injected script running beside unknown page code. Adapt the bundle-path regex and issue-template params. Omit nothing else. No direct test — caveat recorded.
