<!-- capsule-v2 -->
# Unicode-flag regex capability probe — how do you test whether a pattern is valid under `u`/`v` without executing it?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the codebase answer "would this regex be valid WITH the unicode flag?" for suggestion engines like require-unicode-regexp?

## regular-expressions.js validator wrapper
**Path/Symbol:** `lib/rules/utils/regular-expressions.js:isValidWithUnicodeFlag(ecmaVersion, pattern, flag="u")` (:20–56) + `REGEXPP_LATEST_ECMA_VERSION = 2025` (:11). ERRATUM (pass 6 verification, 2026-08-24): earlier draft pinned the const at :15 — off-by-four, never true at either recorded pin (`dc1e7a84`/`c27bc92e`); value `2025` itself verified unchanged.
**Signature:** returns boolean; NEVER throws.
**Data Shape:** version gates first: `u` requires ecmaVersion ≥ 6 (≤5 ⇒ false), `v` requires ≥ 2024 (≤2023 ⇒ false); validator constructed per call with `ecmaVersion: Math.min(ecmaVersion, 2025)` and `validatePattern(pattern, undefined, undefined, {unicode:true}|{unicodeSets:true})`.

### Decisive source
```js
try {
  validator.validatePattern(pattern, void 0, void 0,
    flag === "u" ? { unicode: true } : { unicodeSets: true });
} catch { return false; }
return true;
```

**Flow:** cheap version gate → construct @eslint-community/regexpp validator clamped to the newest grammar it knows → validate → catch-all false.
**Invariant:** the clamp matters both ways — patterns using NEWER-than-config syntax must fail (version fidelity), while config versions beyond regexpp's knowledge still validate against its max (forward compat). try/catch-to-false converts parser exceptions into a clean "not valid" so callers can safely use it inside fix-suggestion ladders (`suggest: isValidWithUnicodeFlag(...) ? [fix] : []`). The u/v flag objects differ (`unicode` vs `unicodeSets`) because regexpp models them as distinct grammars. Consumers: require-unicode-regexp (suggestion viability) and no-misleading-character-class (which checks need which mode).
**Probe:** `tests/lib/rules/utils/regular-expressions.js` (:21–59 matrix: ecmaVersion gates :21/:25, valid/invalid under u :29–45, v-only pattern :52–59).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "isValidWithUnicodeFlag REGEXPP_LATEST_ECMA_VERSION RegExpValidator", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.regular_expressions.isValidWithUnicodeFlag" });
```

## Verdict
Adopt the probe-don't-execute principle whenever a transformation needs to know if a stricter parse would succeed; pin the grammar-version clamp; omit if you never transform regexes.
