<!-- capsule-v2 -->
# dsh-mem0 source attribution + family pattern — how does one plugin mine the whole harness-plugin idiom?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** Why does every write carry a `source` tag, and what does the dsh-mem0 package share verbatim with the sibling plugins it was forked from?

## Telemetry attribution + cross-harness family contract
**Path/Symbol:** `integrations/dsh-mem0/src/index.ts` (`SOURCE = "DEEPSEEK_HARNESS"` :28, comment block :23-27) vs `integrations/pi-agent-plugin/src/memory/{tools.ts,scoping.ts,formatting.ts}`.
**Signature:** `add(messages, { …scopeParams, source: "DEEPSEEK_HARNESS" })`.
**Data Shape:** the tag rides EVERY add call; backend keeps recognized values via a `KNOWN_EVENT_SOURCES` allowlist, unknown values bucket into "OTHERS".

### Decisive source
```ts
// Tags writes so Mem0's backend attributes them to this integration in
// telemetry. The backend keeps recognized values via its KNOWN_EVENT_SOURCES
// allowlist; unknown values bucket into "OTHERS", so "DEEPSEEK_HARNESS" must be
// added to that allowlist for usage to surface by name (a one-line backend PR,
// same pattern as the ZAPIER / STRANDS sources).
const SOURCE = "DEEPSEEK_HARNESS";
```

**Flow:** add → spread `source` alongside camelCase scope params → backend attributes the event if allowlisted. Family: dsh-mem0's `formatting.ts` shares a kernel-identical formatter with `pi-agent-plugin/src/memory/formatting.ts` (same `MemoryLike`, same age ladder, same `[category] text (age) [mem0:id]` line; sibling extras like groupByCategory are additive); `scoping.ts` keeps the identical snake/camel resolver pair with per-call override semantics replacing pi-agent-plugin's project/session/global Scope enum; `output.ts` re-exports the same 200-line/50KB caps.
**Invariant:** Attribution is opt-in at the BACKEND: an unrecognized source string silently vanishes into "OTHERS" telemetry — porting the tag without the allowlist PR loses attribution without any error. The family contract (formatter format, caps, resolver-pair shape) is shared across harnesses on purpose; divergent parts are the tool surface (two fail-soft tools here vs one throwing six-action `mem0_memory` tool) and scoping model (per-call entity overrides vs scope enum). Mine the PATTERN once — this capsule is the decisive instance for all sibling integrations (mem0-plugin, openclaw, strands-mem0, n8n-nodes-mem0, zapier-mem0).
**Probe:** `grep -n 'SOURCE = ' integrations/dsh-mem0/src/index.ts` → exactly :28; `grep -cF 'return `[${cat}] ${mem.memory ?? "(empty)"}${age} [mem0:${mem.id}]`;' <file>` → **1 in BOTH** `integrations/dsh-mem0/src/formatting.ts` and `integrations/pi-agent-plugin/src/memory/formatting.ts` (the shared 4-function kernel — MemoryLike/formatAge/formatMemoryCompact/formatMemoryList — is line-identical; the sibling ADDITIONALLY carries a groupByCategory helper dsh-mem0 omits, so range-diffs are NOT empty); `cd integrations/dsh-mem0 && vitest run` 29/29 green pins the tag's wire position (`{ userId: "u", source: "DEEPSEEK_HARNESS" }`).
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `resolveAddParams` limit 3 → rank #2 twin `integrations.pi-agent-plugin.src.memory.scoping.resolveAddParams` scoping.ts 39-51 surfaces beside the dsh twin (rank #1 :41-53) — the tied-twin page IS the family evidence.

## Verdict
Adopt the source-tag pattern WITH its allowlist prerequisite and treat formatter/caps/resolver shapes as the portable family kernel across Mem0 harness plugins. Adapt the tag value to your integration name. Omit per-sibling capsules until a sibling differs materially (openclaw/strands/n8n/zapier are pattern instances, not new seams).
