<!-- capsule-v2 -->
# Global actor registry — how do you share actor TEMPLATES machine-globally without inheriting session state, tolerating concurrent writers and corrupt files?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what does a project-independent actor template library persist, what does it deliberately strip, and how does it load untrusted JSON defensively?

## Template store: identity stripped on export, re-validated per field on patch
**Path/Symbol:** `src/actors/global-registry.ts:GlobalActorRegistry` (:76-385), `resolveDefinition` (:46-58), `#validate` (:228-294), `#load` (:296-379).
**Signature:** `create(def: FabricActorRequest, overwrite = false)`, `update(idOrName: string, patch: Partial<FabricActorRequest>)`, `resolve(idOrName)` (exact id → exact name → unique id-prefix; ambiguous prefix **throws**), `toRequest(def, as?)`, all returning `structuredClone`d values.
**Data Shape:** file `<agentDir>/fabric/actors/global-actors.json` = `{format: 1, actors: GlobalActorDefinition[]}`; definition = request fields + `{id: 32-hex, createdAt, updatedAt}`.

### Decisive source
```ts
// Templates carry definitions + identity only — never history. Importing into
// a project creates a FRESH live actor: no session, mailbox, or run logs.
toRequest(def, as?) {
  const name = as?.trim() || def.name;
  return { name, instructions, events: [...def.events], topics: [...def.topics],
    delivery, responseMode, triggerTurn, coalesce,
    ...(def.residency ? { residency } : {}), ... };   // identity/timestamps GONE
}
// Load is total defensive normalization: one bad record skips, never throws.
if (typeof record.id !== "string" || !/^[a-f0-9]{32}$/.test(record.id) || ...) continue;
const delivery = record.delivery === "steer" || ... ? record.delivery : "mailbox"; // degrade
const validWhile = record.validWhile?.version === 1 &&
  typeof record.validWhile.source === "string" && record.validWhile.source.length <= 16_000
  ? clone(record.validWhile) : undefined;             // oversize predicate silently dropped
```
```ts
// update(): merge ONLY supplied fields, then RE-VALIDATE the merged whole and
// guard the rename path against cross-id name clashes before saving atomically.
```

**Flow:** constructor loads once (ENOENT and even parse errors tolerated → empty registry; `/fabric reload` re-reads other sessions' additions) → create/update validate through the same gate as live actors (`resolveActorDeliveryPolicy`, byte-limited instructions, topic pattern, transport allowlist) → every write goes through `writeJsonAtomic` (temp+rename), so concurrent sessions can't corrupt the store though simultaneous edits are last-write-wins → import path strips identity via `toRequest`.
**Invariant:** stored data is never trusted on load — every field is re-checked against the current patterns/enums and degraded to defaults (mailbox/text/pi runner) or skipped; validation errors throw at API time but never during load. Reads always hand out clones; prefix resolution must fail LOUDLY on ambiguity.
**Probe:** `tests/global-registry.test.ts:33` ("creates, lists, and resolves templates by id, prefix, and name"), `:52` (persists across instances), `:61` (duplicate-name overwrite rules), `:119` (validation of names/instructions/events/topics/sizes), `:134` ("strips identity and timestamps in toRequest"), `:156` (legacy trigger normalization), `:195` ("throws when a query matches multiple templates").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "GlobalActorRegistry resolveDefinition toRequest validate global-actors.json atomic", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt templates-without-history (identity stripped at export, fresh runtime object on import), loud ambiguity on prefix resolve, skip-not-throw loading, and atomic last-write-wins persistence; adapt the field set/patterns and the reload trigger; omit pi's delivery vocabulary (covered by actor-delivery-policy-triad).
