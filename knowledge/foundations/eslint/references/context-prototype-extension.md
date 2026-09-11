<!-- capsule-v2 -->
# Frozen prototype-chained context extension — why Object.create instead of spread when per-rule contexts multiply?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does FileContext give every rule a customized context without copying the shared base N times?

## FileContext.extend
**Path/Symbol:** `lib/linter/file-context.js:FileContext` (:11–88) — frozen in constructor (:73), `extend(extension)` (:83–85).
**Signature:** `extend(extension): FileContext` — `Object.freeze(Object.assign(Object.create(this), extension))`.
**Data Shape:** own properties = ONLY the extension; everything else resolves through the prototype chain to the single frozen base instance.

### Decisive source
```js
constructor({ cwd, filename, physicalFilename, sourceCode, languageOptions, settings }) {
  this.cwd = cwd; /* ... */
  Object.freeze(this);
}
extend(extension) {
  return Object.freeze(Object.assign(Object.create(this), extension));
}
```

**Flow:** base context constructed once per file → each rule's listener assembly calls extend({id, options, report}) → rule sees a flat-looking object.
**Invariant:** the base is FROZEN so prototype-chain inheritance is safe (no rule can mutate what siblings inherit); each derived object is separately frozen so rules can't graft onto their own context either. Spread/`Object.assign({}, base, ext)` would be O(fields×rules) AND break identity checks (`extended.sourceCode === base.sourceCode` still holds here because values are shared by reference through the chain). Property shadowing means a rule reading `context.options` gets its OWN while `context.cwd` walks up — transparent unless someone enumerates own-keys expecting the full set. This is the mechanism behind "ONE frozen FileContext extended per rule" (vfile-context-identity capsule).
**Probe:** `tests/lib/linter/file-context.js` (:30–75 constructor freezing + property pinning; :77–110 extend: new-property presence, inherited equality via deepStrictEqual, freeze of the extended object).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "FileContext extend Object.create freeze", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.file_context.FileContext.extend" });
```

## Verdict
Adopt for any hot path handing N consumers a personalized view of one shared immutable record; document the own-enumeration caveat for consumers who serialize contexts.
