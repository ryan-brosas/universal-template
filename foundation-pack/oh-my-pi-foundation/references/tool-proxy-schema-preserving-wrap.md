<!-- capsule-v2 -->
# Schema-preserving tool wrapping — how do you proxy an object that mixes methods with CALLABLE schemas without destroying the schema surface?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** Wrapping a tool by copying properties breaks ArkType-style schemas — why, and what is the forwarding rule that survives?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/tool-proxy.ts:applyToolProxy` (:1-35 whole); consumers `custom-tools/wrapper.ts:CustomToolAdapter` (:1-50) and `extensions/wrapper.ts` / `hooks/tool-wrapper.ts` constructors; direct tests `test/extensibility/tool-proxy.test.ts` (:1-59 whole).
**Signature:** `applyToolProxy<TTool extends object>(tool: TTool, wrapper: object): void` — defines lazy getter properties on the wrapper.
**Data Shape:** walks prototype chain via `Object.getPrototypeOf` collecting `Reflect.ownKeys`; skips `constructor`, already-visited keys, and any key already present on the wrapper (wrapper own declarations win); binds only "genuine methods".

### Decisive source
```ts
// Callable schema values (ArkType `Type`, e.g. the `parameters` schema)
// must pass through untouched: `bind()` returns a bare bound function
// that drops the schema surface (`toJsonSchema`/`assert`/own keys), so a
// bound schema later stringifies to `undefined` and poisons wire-schema
// and token accounting. Only genuine methods are bound so `this` is
// preserved through the wrapper.
if (isArkSchema(value) || typeof value.bind !== "function") return value;
return value.bind(tool);
```
**Flow:** wrapper constructor calls applyToolProxy(tool, this) -> every later property read forwards lazily -> methods get `this` bound to the INNER tool even when invoked off the wrapper -> callable schemas pass through BY REFERENCE so isArkSchema stays true downstream.
**Invariant:** (1) never bind a value that is itself a schema/callable carrying its own API surface; (2) wrapper-declared members (name/label/description/execute) are NOT shadowed by proxies; (3) enumerable+configurable getters keep JSON serialization of plain data working. Two pinned regressions in the direct test: omptype schemas (plain functions with own toJsonSchema/assert) and external-arktype copies whose Type DOES have Function.prototype.bind — both must survive as unbound callables or toolWireSchema yields undefined and the tokenizer crashes every read-only subagent at first prompt.
**Probe:** `test/extensibility/tool-proxy.test.ts`: `expect(isArkSchema(wrapper.parameters)).toBe(true)`; `expect(wrapper.parameters).toBe(schema)` (identity for external arktype); `execute.call({ name: "WRONG" })` resolves to inner name.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "applyToolProxy", limit: 10 });
```

## Verdict
Adopt: lazy prototype-walk forwarding with the never-bind-callable-schemas rule and visited-set dedupe. Adapt: your schema-detection predicate in place of isArkSchema. Omit: nothing — the whole file is the primitive.
