<!-- capsule-v2 -->
# dsh-mem0 compact memory rendering — what does one memory cost in model tokens?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** How should search results be rendered into model context so the tokens go to facts, not JSON scaffolding?

## One-line-per-memory formatter
**Path/Symbol:** `integrations/dsh-mem0/src/formatting.ts` (`formatAge` 17-26, `formatMemoryCompact` 28-32, `formatMemoryList` 34-39).
**Signature:** `formatMemoryList(memories: MemoryLike[]): string` over `MemoryLike = { id: string; memory?: string; categories?: string[]; createdAt?: Date | string }`.
**Data Shape:** output lines are `[category] text (age) [mem0:id]`, numbered `N. ` by `formatMemoryList`; every field degrades independently.

### Decisive source
```ts
const cat = mem.categories?.[0] ?? "uncategorized";
const age = mem.createdAt ? ` (${formatAge(mem.createdAt)})` : "";
return `[${cat}] ${mem.memory ?? "(empty)"}${age} [mem0:${mem.id}]`;
// list: memories.length === 0 ? "No memories found." : numbered join("\n")
// age ladder: <60m → "Nm ago", <24h → "Nh ago", else "Nd ago"
```

**Flow:** first category or "uncategorized" → text or "(empty)" → optional humanized age (string dates re-parsed) → always terminate with `[mem0:id]`.
**Invariant:** The format is a deliberate cross-harness CONTRACT — byte-identical to the sibling plugins (`integrations/pi-agent-plugin/src/memory/formatting.ts`) so a memory reads the same way from any harness; keep it stable. Every degradation is per-field and total: missing categories/text/createdAt never throw, and the trailing id token is ALWAYS present so the model can cite/update/delete later.
**Probe:** `integrations/dsh-mem0/tests/formatting.test.ts` ("renders one line with category, text, and id"; fallback test asserts BOTH `[uncategorized]` and `(empty)` appear for `{ id: "x" }`; empty list returns exactly `"No memories found."`; age ladder 30m/3h/5d) — green offline.
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `formatMemoryCompact` limit 3 → `integrations.dsh-mem0.src.formatting.formatMemoryCompact` formatting.ts 28-32 rank 1 line-exact.

## Verdict
Adopt the one-line contract verbatim (bracket-category, space-text, paren-age, bracket-id) including its per-field fallbacks — it is the shared family wire format across harness plugins. Adapt only the id prefix label if your host namespaces differently. Omit richer rendering (tables/JSON) — that reintroduces the scaffolding-token cost this exists to avoid.
