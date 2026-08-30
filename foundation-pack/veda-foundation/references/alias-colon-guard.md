<!-- capsule-v2 -->
# Alias parsing — colon-safe reasoning suffix via validated-tail check, user-over-builtin precedence

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (pass-9 re-adjudication: `git diff f050518c..c3c69f2 -- src/agent/model-aliases.ts` shows ONE additive alias-table row (`daybreak-blue`); parsing functions byte-identical, line anchors re-verified at pin); Codebase Memory `veda`. **Question:** How do I parse `name=model[:reasoning]` alias entries when model ids themselves contain colons?

## MODEL_ALIASES config grammar + prefix→backend inference
**Path/Symbol:** `src/agent/model-aliases.ts:parseModelAliases` (:43–77), `inferAliasBackend` (:76–90), `resolveModelAlias` (:96–101) — line ranges re-verified at pin c3c69f2 (pass 9).
**Signature:** `function parseModelAliases(value: string): UserAliases`; `function resolveModelAlias(model: string, extraAliases?: UserAliases): ModelAliasTarget | undefined`.
**Data Shape:** Entries comma-separated; `REASONING_LEVELS = Set('minimal','low','medium','high','xhigh','max')`; built-in table maps friendly names (`opus`, `sol`, `gemini-pro`, …) to `{ backend, model, reasoning? }`.

### Decisive source
```ts
// The optional :reasoning suffix only counts when the trailing segment is a
// valid reasoning level. This keeps colons inside the model id (e.g. pi's
// hf:moonshotai/Kimi-K3) from being misread as a reasoning separator.
let model = target;
let reasoning: string | undefined;
const lastColon = target.lastIndexOf(':');
if (lastColon !== -1) {
  const tail = target.slice(lastColon + 1).toLowerCase();
  if (REASONING_LEVELS.has(tail)) {
    reasoning = tail;
    model = target.slice(0, lastColon);
  }
}
```

**Flow:** split on commas → require `=` → name lowercased, target kept caseful → try splitting at the LAST colon ONLY if the tail is a whitelisted reasoning word (else the whole string stays the model id) → infer backend from model prefix (`pi/`, `agy/`, `gpt-`, `o1-`, `o3-`, `claude-`) → invalid entries are SKIPPED silently, never thrown. Lookup order: user aliases override built-ins ("config is an override layer").
**Invariant:** The suffix is recognized by VALIDATION, not position: a non-reasoning tail (`hf:moonshotai/Kimi-K3`) leaves the model intact. A positional `split(':')` port corrupts such ids. Invalid entries skip rather than abort so one typo cannot break the whole alias table.
**Probe:** `tests/agent/model-aliases.test.ts` — dedicated suite covering the alias table and parse polarities (colon-in-model vs real reasoning suffix among them).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "parseModelAliases inferAliasBackend REASONING_LEVELS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the validated-tail colon guard and silent-skip entry handling verbatim; adopt the six-level reasoning vocabulary as-is if your host speaks OpenAI-style effort tiers. Adapt the built-in name table and prefix→backend list to your fleet. Omit nothing else.
