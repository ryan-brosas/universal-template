<!-- capsule-v2 -->
# Extension bootstrap & closure state — where does extension state live, and which lifecycle surfaces are real?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must know what the host actually calls, where per-session state lives across event invocations, and which documented lifecycle surfaces exist only on paper.

## Default-export factory + per-instance closure state (`pi-memory.ts:1–5`, `:235–242`)
**Path/Symbol:** module imports :1–5; factory `export default function (pi: ExtensionAPI)` :235; closure state :236–237.
**Signature:** `export default function (pi: ExtensionAPI): void` — no named exports, no class; the whole extension is one factory closing over two locals.
**Data Shape:** `let config = { ...DEFAULT_CONFIG }` (shallow snapshot of :26–33) and `let cache: MemoryCache | null = null` — ALL mutable state is per-factory-invocation closure state; there is NO module-level mutable binding.

### Decisive source
```ts
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
...
export default function (pi: ExtensionAPI) {
  let config = { ...DEFAULT_CONFIG };
  let cache: MemoryCache | null = null;
```

**Flow:** host discovers entry via package.json `pi.extensions` → calls factory once with the extension API → every handler/command closes over the same `config`/`cache` pair → `session_start` rebuilds `cache` wholesale (:268); nothing else ever reassigns it except `/memory:refresh` (:318–349).
**Invariant:** State isolation comes from the closure, not from a store: two instances of this extension would not share cache. The config snapshot is SHALLOW — `priority`/`globalAlwaysInject` array fields are shared by reference with DEFAULT_CONFIG (harmless only because config is never mutated anywhere after the spread; verified by executed probe). Both session-bound handlers open with `if (!cwd) return;` (:242, :381) — a missing cwd silently disables the extension rather than erroring. PHANTOM SURFACES at this pin: (1) `ExtensionContext` imported at :1 and used NOWHERE (grep: line 1 only); (2) design.md:348 Event Map documents `session_shutdown | No automatic cleanup`, but source has ZERO `session_shutdown` matches — the real event surface is exactly three `pi.on` registrations (:240/:277/:289). The asymmetry is deliberate-looking but easy to mis-port: `agent_settled` is registered-EMPTY as living documentation of no-auto-write, while `session_shutdown` is documented-but-unregistered. Copy behavior, not the doc table.
**Probe:** No upstream test suite exists. Pass-4 executed probes (inline `node -e`, Node v26.7.0): shallow-spread semantics GREEN ×2 (primitive field edits independent of DEFAULT_CONFIG; array fields shared by reference). Mechanical greps at HEAD: `ExtensionContext|Type|ExtensionAPI` ⇒ ExtensionContext :1-only; `pi\.on\(|registerCommand\(` ⇒ exactly 10 sites (3 events + 7 commands), `session_shutdown` ⇒ 0. Startup telemetry contract read directly at :270–273 (`🧠 Pi Memory: G global + W workspace = M files` notify — counts are PRE-merge layer counts plus merged total).
**Adversarial retrieval:** BM25 `"command arguments typed validation schema"`-style generic queries miss this plane entirely; `search_graph name_pattern "^(bootstrap|main|entrypoint|lifecycle)$"` returns only the git `main` Branch node — the factory is anonymous, so resolve by content search (`search_code "export default function"` ⇒ single hit :235).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "pi-memory-extension", pattern: "export default function", limit: 5 });
```
(Executed pass 4: exactly one match, Module `pi-memory.ts` line 235.)

## Verdict
Adopt the one-factory/closure-state shape for any host extension: default-exported registrar, nullable cache handle rebuilt only at explicit reload points, config snapshotted once. Adapt state placement to the host DI model if it offers real instance scoping. Omit phantom surfaces consciously — implement `session_shutdown` only if your port needs teardown, and delete the dead import rather than shipping decorative types. Coverage caveat: no upstream suite; pinned by executed probes + byte-cited ranges.
