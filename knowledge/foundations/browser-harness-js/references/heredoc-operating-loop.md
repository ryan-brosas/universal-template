<!-- capsule-v2 -->
# Heredoc operating loop — how does an agent compose observe → act → verify → return without paying a tool-call round trip per step?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the operating discipline that makes multi-step browser tasks finish in one composed script instead of chained CLI calls, and which lifecycle rules keep that composition correct?

## One heredoc per round; three workflows in preference order; helpers are recipes, never wrappers
**Path/Symbol:** `skills/cdp/interaction-skills/agent-operating-loop.md` (whole doc, 114L: loop :21-38, workflows :40-76, anti-patterns :78-98, self-documentation :100-103); corroborated by `skills/cdp/sdk/helpers.ts` header ethos (:1-6), `drainSignals` lazy attach (:180-183), `pageInfo` race (:193-211), `HELP` table (:280-301).
**Signature:** each REPL round is one `browser-harness-js <<'EOF' … EOF` script shaped `observe -> act -> verify -> return`; return-value render table: bare strings print raw, arrays/objects print as compact JSON, undefined/null/""/{}/[] print nothing.
**Data Shape:** three workflows picked in order — Semantic (`axView({interactive:true})` + refs/locators + `axDiff`) → Visual (`Page.captureScreenshot` + viewport-coordinate `Input.*`) → Direct-DOM/CDP (`Runtime.evaluate`, `DOM.*`, `cdp(sessionId,…)`).

### Decisive source
```ts
// helpers.ts:1-6 — the design law the whole doc leans on:
// "These exist for things CDP structurally LACKS — never to wrap or hide a
// CDP method (the SDK's ethos: if Chrome can do it, call it directly)."
function drainSignals(): string[] {
  attachSignals();                       // :181 — LAZY attach on first drain
  return _signalQueue.splice(0, _signalQueue.length);
}
```
and the doc's loop contract (agent-operating-loop.md :25-36): arm `attachSignals()` BEFORE the action when events matter; act on a `[n]` ref or a stable `loc=role:R["N"]` locator; verify via `axDiff(prev, next)` against a fresh snapshot instead of re-feeding the whole tree.

**Flow:** pick the workflow by page type (semantic default; visual only when the AX tree lies or is missing; raw CDP for state/custom traversal) → compose the ENTIRE round in one heredoc over the shared WebSocket + persistent session → observe (snapshot or armed signals) → act on ref/locator → verify with axDiff or screenshot read-back → `return` one compact value → next heredoc only when fresh page state or human handoff (login/captcha) demands it.
**Invariant:** (1) THE HEREDOC IS THE COMPOSITION PRIMITIVE — every CLI-chained step re-pays discovery/context tokens; parallel-safe because sessions are per-call sessionIds. (2) `[n]` refs are valid only within ONE `getFullAXTree`: after navigation/mutation re-snapshot, or use `locators:true` (`parseAxLocators`) whose role+name survive rebuilds. (3) Events fired BEFORE `attachSignals()`/`drainSignals()` DO NOT EXIST — drainSignals' first-line lazy attach (:181) is exactly why arming must precede the action. (4) A native dialog blocks `Runtime.evaluate` forever: race it (`pageInfo` returns `{dialog}` / `{unresponsive}`, never hangs) and dismiss via `Page.handleJavaScriptDialog` before anything else works. (5) Browser-side logic stays in ONE explicit IIFE with one `return` — every extra eval is another round trip and escaping layer. (6) Helpers close over `globalThis.session` read per call, so reconnects swap transparently; they must never grow into wrappers that hide a `session.Domain.method` call. (7) `help()` / `help('axClick')` is the in-context documentation surface so the model doesn't reload docs mid-task.
**Probe:** no direct unit test drives a doctrine doc; deterministic probes pin both halves — `grep -n "structurally LACKS" skills/cdp/sdk/helpers.ts` (:3) pins the ethos; `grep -n "^function drainSignals" skills/cdp/sdk/helpers.ts` (:180) plus reading :181 shows the lazy attach; `grep -n "## The loop\|## Anti-patterns" skills/cdp/interaction-skills/agent-operating-loop.md` (:21, :78) pins the doc sections quoted above.
**Coverage caveat:** doctrine capsule — behavior claims about the loop itself rest on the curated doc; every mechanical claim (lazy attach, dialog race, locator grammar) is independently covered by source-cited capsules (agent-signals-digest, page-info-probe, ax-locator-resolution).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "drainSignals", limit: 3, fields: ["signature", "name", "file"] });
// resolves browser-harness-js.skills.cdp.sdk.helpers.drainSignals @ helpers.ts:180-183  (executed this pass)
```

## Verdict
Adopt the one-heredoc-per-round loop and the semantic→visual→CDP preference order for any LLM-driven browser harness — the token economics and verification discipline transfer intact. Adapt the helper roster and render-table details to your REPL. Omit nothing from the anti-pattern list lightly: each one encodes a reproduced failure (stale refs, missed early events, modal hang).
