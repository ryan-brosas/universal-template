<!-- capsule-v2 -->
# Proxy self-disable gate — should this extension register anything when another plugin already owns its tools?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** When my extension can collide with a sibling plugin that handles the same tool names natively, what is the safe coexistence contract for the entry-point factory?

## Env-gated no-op factory body
**Path/Symbol:** `src/index.ts`:41-63 (`createAcpExtension`, the sole export); gate at :43-46; full wiring ladder :47-61; `wireCompactionDisable` :69-71 (first real side effect when NOT gated).
**Signature:** `export function createAcpExtension(adapter: AdapterConfig = {}): ExtensionFactory` — returns `(pi: ExtensionAPI) => void`.
**Data Shape:** gate reads `process.env.BILLION_CONTEXT_PROXY` as a TRUTHY check (set by the `bili pi` launcher; unset-or-empty = standalone mode). When gated, the factory performs exactly one observable action — `console.log("[bcp] disabled: BILLION_CONTEXT_PROXY detected — proxy handles compression")` — and returns without touching `pi`.

### Decisive source
```ts
// src/index.ts:41-48 — the ENTIRE drift seam of upstream v0.1.47 (commit d3e1bf8,
// "fix: self-disable when running under billion-context proxy"):
export function createAcpExtension(adapter: AdapterConfig = {}): ExtensionFactory {
  return (pi: ExtensionAPI) => {
    if (process.env.BILLION_CONTEXT_PROXY) {
      console.log("[bcp] disabled: BILLION_CONTEXT_PROXY detected — proxy handles compression");
      return;
    }
    const runtime = createRuntime(adapter);
```

**Flow:** host invokes factory → env gate fires FIRST, before ANY side effect → gated: single console.log line, zero tools (`compress`, `decompress`, `search_context`, `acp_status`), zero commands (`/acp`), zero event handlers, and crucially NO `createRuntime` construction → ungated: compaction-cancel wiring, session lifecycle, context transform, system prompt, guardrails, overflow self-heal, throttle retry, then the four tools + commands register in fixed order.
**Invariant:** (1) The gate must precede `createRuntime` — runtime construction opens the fail-silent log stream and allocates per-session state; a porter who registers nothing but still builds the runtime leaks resources into sessions the extension will never serve. (2) Presence beats value: any non-empty string disables; there is no "off" value grammar to honor. (3) The reason is NAME CONFLICTS, not double work — both packages would register identically-named tools/commands and the host registry cannot hold both; a port that renames either side must still keep exactly one owner per name. (4) Silent step-aside (log only, no error, no notify) is deliberate: under `bili pi` the proxy plugin handles all ACP tools natively, so bcp disappearing IS the correct user-visible behavior.
**Probe:** `cd $REFERENCE_ROOT/coding-agents/billion-context-pi && grep -cF "BILLION_CONTEXT_PROXY" src/index.ts` → `2` (gate condition :43 + message :44); ordering anchor: gate line number (`grep -n 'process.env.BILLION_CONTEXT_PROXY' src/index.ts | head -1 | cut -d: -f1` → `43`) must be LESS than runtime-construction line (`grep -n 'const runtime = createRuntime' src/index.ts` → `47`). No dedicated test file pins index.ts (host-factory surface) — these greps ARE the executable anchors at pin; battery /tmp/dl-bcp5-battery-v2.sh 15/15 GREEN ×2 incl. both suites below.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "createAcpExtension registerTool compress decompress compaction", limit: 10 });
```

## Verdict
Adopt the pattern: an entry-point factory whose very first statement is a truthy-env bail-out with a single diagnostic log, used whenever a sibling/plugin may own your tool names. Adapt the env-var name, the log channel, and which registrations are conflict-prone to your host. Omit nothing from the bail-out — partial registration under the gate is the bug class this seam exists to prevent. Coverage caveat: graph freshness proven by `search_code "BILLION_CONTEXT_PROXY"` resolving src/index.ts:43-44 at the pin (content-refresh check after in-place re-index).
