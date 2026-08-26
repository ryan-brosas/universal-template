<!-- capsule-v2 -->
# Prototype-safe lookup — why must every model-controlled name resolve through an own-property read?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Why does bracket access on a tool set or refinement map let model output reach code that was never registered, and what is the one-helper fix?

## getOwn
**Path/Symbol:** `packages/ai/src/util/get-own.ts:11-18` (`getOwn`).
**Signature:** `getOwn<T extends object>(obj: T | undefined | null, key: string): T[keyof T] | undefined`.
**Data Shape:** In: any lookup object keyed by untrusted names (tool sets, tool contexts, refineToolInput maps); out: own property value or `undefined`.

### Decisive source
```ts
// Tool sets, tool contexts, and similar lookup objects are indexed by names
// that can come from model output or client-supplied message history. Plain
// bracket access (obj[name]) resolves names such as 'constructor',
// 'toString', or '__proto__' to values on Object.prototype, which would slip
// past the == null / !value guards that treat an unknown name as "not present".
export function getOwn<T extends object>(obj: T | undefined | null, key: string): T[keyof T] | undefined {
  return obj != null && Object.hasOwn(obj, key) ? obj[key as keyof T] : undefined;
}
```

**Flow:** This is the repo-wide repeated pattern (SIMILAR_TO across every consumer of untrusted keys): `parse-tool-call.ts` resolves tools AND refinements via `getOwn`; the approval/id maps use prototype-less `Object.create(null)` (`createIdMap`, see event-ledger capsule) — two defenses for the same attack class. Model says `"toolName": "constructor"` ⇒ plain bracket finds `Object.prototype.constructor` (truthy!) ⇒ parse proceeds against a non-tool ⇒ type confusion or crash; `getOwn` yields `undefined` ⇒ clean `NoSuchToolError`.

**Invariant:** Any key originating outside your program (model output, client history) MUST go through own-property semantics before a truthiness gate. An inherited value passing `== null` checks is the exact failure mode.

**Probe:** `packages/ai/src/util/get-own.test.ts:13` ("returns undefined for inherited object properties rather than a prototype value"), `:19` (own property shadows inherited name), `:23` (null/undefined obj safe). Consumer-side pin: `packages/ai/src/generate-text/parse-tool-call.test.ts:83` ("should not treat an inherited object property as a refinement for a tool whose name collides with it").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getOwn Object.hasOwn", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the helper verbatim (it is portable as-is). Adapt naming to host conventions; do NOT adopt only half of it — pair with prototype-less maps when constructing id-keyed accumulators.
