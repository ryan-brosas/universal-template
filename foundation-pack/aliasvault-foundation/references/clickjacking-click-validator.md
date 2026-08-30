<!-- capsule-v2 -->
# Clickjacking click validator — which page-level visual manipulations void a user click before autofill?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What checks gate a content-script click, and what is the fail-safe direction?

## Opacity/filter + gesture validation
**Path/Symbol:** `apps/browser-extension/src/utils/security/ClickValidator.ts:24-47` (`validateClick`), :52-106 (`detectPageOpacityTricks`), :111-132 (`validateGesture`).
**Signature:** `public async validateClick(event: MouseEvent): Promise<boolean>`; singleton `getInstance()`.
**Data Shape:** Inspects computed styles of `documentElement` and `body` only (page-wide tricks, not per-element); threshold `opacity < 0.9`; any non-`none` CSS filter counts; gesture requires left-button (0) + coordinates inside viewport.

### Decisive source
```ts
if (htmlOpacity < 0.9) {
  return { detected: true,
    reason: `HTML element opacity reduced to ${htmlOpacity} - potential clickjacking attempt` };
}
// Check for CSS filters that could obscure content
if (htmlStyle.filter && htmlStyle.filter !== 'none') {
  return { detected: true,
    reason: `HTML element has CSS filter applied: ${htmlStyle.filter} - potential visual manipulation` };
}
...
} catch (error) {
  return { detected: true, reason: `Error checking page opacity: ${error}` };
}
```

**Flow:** click → opacity/filter scan (HTML then BODY, short-circuit on first detection) → gesture check → allow. Any thrown error inside the opacity scan is treated as DETECTED — the validator fails CLOSED.
**Invariants:** (1) Fail-closed: an exception in the checker itself rejects the click (:100-105 returns detected:true in catch; validateClick catch also returns false). (2) Scope is deliberately BODY/HTML only so ordinary overlays don't false-positive; the doc header says "simplified for content script shadow DOM scenarios". (3) Non-left clicks never trigger credential fill. (4) Reasons double as user-facing diagnostics — keep the "potential clickjacking attempt" phrasing stable if ported.
**Probe:** `grep -c 'potential clickjacking attempt' apps/browser-extension/src/utils/security/ClickValidator.ts` → `2`; `grep -c 'detected: true' apps/browser-extension/src/utils/security/ClickValidator.ts` → `5` (html-opacity, html-filter, body-opacity, body-filter, catch fail-closed).

## Direct tests
**Path/Symbol:** fixture `apps/browser-extension/src/utils/security/__tests__/clickjacking-test.html` (upstream manual harness; no automated jest spec for this class).
**Probe:** `grep -rc 'validateClick' apps/browser-extension/src --include='*.ts' | grep -v dist | head -5` (call sites resolve); deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "detectPageOpacityTricks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-closed page-level opacity/filter gate before any autofill action; extend to per-element analysis at your own risk (upstream chose not to); omit singleton plumbing. Source confirmed at pin `95903e92`.
