<!-- capsule-v2 -->
# IdGenerator + visitor registry — the two micro-primitives every linter core needs (wrap-safe unique ids; multi-subscriber event names)

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What do the smallest reusable pieces of this subsystem look like, and what contract makes them safe to copy?

## IdGenerator + SourceCodeVisitor
**Path/Symbol:** `lib/linter/code-path-analysis/id-generator.js:IdGenerator` (:19–41); `lib/linter/source-code-visitor.js:SourceCodeVisitor` (:23–79).
**Signature:** `new IdGenerator(prefix?)`; `next() → prefix + n`. Visitor: `add(name, fn)`, `get(name)`, `forEachName(cb)`, `callSync(name, ...args)`.
**Data Shape:** ids are `s1, s2…` per analyzer plus per-path prefixed `${pathId}_${n}` (each CodePath news its own generator seeded with the path id — see `code-path.js:60`); visitor maps name → Function[] with a SHARED frozen empty array for misses.

### Decisive source
```js
next() {
  this.n = (1 + this.n) | 0;      // 32-bit wrap...
  if (this.n < 0) this.n = 1;     // ...resets to 1 instead of going negative
  return this.prefix + this.n;
}
// visitor:
get(name) {
  return this.#functions.has(name) ? this.#functions.get(name) : emptyArray;
}
callSync(name, ...args) {
  if (this.#functions.has(name)) this.#functions.get(name).forEach(func => func(...args));
}
```

**Flow:** CodePathAnalyzer owns one generator for path ids; each CodePath owns one for its segment ids (`s3_12` style), so segment ids are unique within a path and path-prefixed globally. Rules register selector listeners via `visitor.add` in rule order; traversal calls them in registration order per selector.
**Invariant:** the 32-bit wrap MUST reset to 1, not 0, or id `s0`/duplicate first ids appear after ~2³¹ segments (tests pin `s${n}` starting at 1); `get()` returning a frozen shared empty array lets callers iterate without null checks without risking cross-instance mutation; callSync on unknown name is a silent no-op by design (rules legitimately don't listen to every event).
**Probe:** `tests/lib/linter/code-path-analysis/id-generator.js` (whole-file :1–58); `tests/lib/linter/source-code-visitor.js` (:35–186 add/get/forEachName/callSync incl. frozen-empty-array + registration-order assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "IdGenerator next SourceCodeVisitor callSync forEachName", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.source-code-visitor.SourceCodeVisitor.callSync" });
```

## Verdict
Adopt both verbatim (tiny, zero-dep); adapt prefixes/naming to your host; omit nothing.
