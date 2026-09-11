<!-- capsule-v2 -->
# Alias-table drift discipline — adding a slug is a table row PLUS its test lattice, never just the row

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `mnt-hdd-utopia-inspo-pi-ecosystem-veda`. **Question:** When a lookup-table entry doubles as public CLI surface (users type the alias), what must change together so docs, resolution, and listing stay truthful?

## MODEL_ALIASES row + five-point test lattice
**Path/Symbol:** `src/agent/model-aliases.ts:MODEL_ALIASES` (:18 new `daybreak-blue` row); consumers `resolveModelAlias` (:96), `parseModelAliases` (:43), `inferAliasBackend` (:76) unchanged by this drift; `tests/agent/model-aliases.test.ts` (:22–23, :70, :110, :137, :147, :151).
**Signature:** `'daybreak-blue': { backend: 'codex', model: 'gpt-daybreak-blue-latest', reasoning: 'high' }`.
**Data Shape:** Alias name ≠ API-doc model id: the CLI slug `daybreak-blue` maps to wire model `gpt-daybreak-blue-latest`. The alias carries an implied default reasoning (`high`) that flows through resolveModelAlias when no `-r` flag is given (see model-resolution capsule for that precedence chain).

### Decisive source
```ts
// tests/agent/model-aliases.test.ts — every new row is pinned at FIVE points:
expect(MODEL_ALIASES['daybreak-blue']).toEqual({ backend: 'codex', model: 'gpt-daybreak-blue-latest', reasoning: 'high' }); // :22-23 "never the API-doc ID daybreak-blue-latest"
expect(resolveModelAlias('daybreak-blue')).toEqual({ ... });        // :70 resolution
expect(isModelAlias('daybreak-blue')).toBe(true);                   // :110 membership
expect(aliases).toContain('daybreak-blue');                         // :137 listed
expect(aliases).not.toContain('daybreak-blue-latest');              // :147 NEVER the raw model ID
// :151 comment — 10 built-in aliases counted explicitly
```

**Flow:** user types `-m daybreak-blue` → resolveModelAlias hits the table → backend/model/reasoning feed the same precedence ladder as explicit flags. The listing surface (`aliases`) is DERIVED from the table, which is why a hand-edited doc list would rot — and why the test asserts both containment of the slug AND exclusion of the raw id.
**Invariant:** An alias is public vocabulary: adding one without updating the test lattice leaves resolution working but listing/docs lying. The slug-vs-wire-id split must be preserved end-to-end (the test comment calls it out verbatim). Counting the table in tests (:151) makes accidental removals visible too.
**Probe:** `grep -c 'daybreak' tests/agent/model-aliases.test.ts` → 6; `grep -n "'daybreak-blue':" src/agent/model-aliases.ts` → exactly :18.
**Count check:** `sed -n '18p' src/agent/model-aliases.ts | grep -c 'gpt-daybreak-blue-latest'` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "MODEL_ALIASES daybreak resolveModelAlias", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the rule: public-vocabulary table rows ship with their assertion lattice in one commit. Adapt alias names/reasoning defaults. Omit veda's specific slugs. Coverage note: pinned directly by the dedicated model-aliases suite.
