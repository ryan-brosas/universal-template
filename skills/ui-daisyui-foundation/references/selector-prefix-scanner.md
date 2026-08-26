<!-- capsule-v2 -->
# Selector-prefix scanner — how do I prefix every class and CSS variable in a styles tree without corrupting strings, comments, escapes, or attribute selectors?

**Source:** daisyUI MIT `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory `ui-daisyui`. **Question:** What state machine correctly rewrites `.btn:hover, [dir='rtl'] .icon` *and* `var(--custom-var)` values under a prefix, while leaving `.prose`, calendar libs, and `--tw-*` untouched?

## Character-level scanner + exclusion lists
**Path/Symbol:** `packages/daisyui/functions/addPrefix.js:74-136` (`prefixSelectorClasses`) with key dispatch at `getPrefixedKey:138-156` and value rewriting at `processStringValue:175-184`.
**Signature:** `addPrefix(obj, prefix, excludedPrefixes = defaultExcludedPrefixes) → obj`.
**Data Shape:** input is a CSS object (selectors/`@`-keys → string|object|array). Scanner state: `quote` (`"`/`'`), block-comment skip, backslash escape spans via `getEscapeEnd` (hex-escape aware, ≤6 digits + optional trailing whitespace), `attributeDepth` counter for `[...]`. Excluded variable prefixes default to `["color-", "size-", "radius-", "border", "depth", "noise"]` plus always `tw*`; excluded selector names include `prose`, `is-*`/`pick-whole-week`, and third-party `rdp-|pika-|vc-`.

### Decisive source
```js
if (character === "." && attributeDepth === 0 && isIdentifierCharacter(selector[index + 1])) {
  const identifierEnd = getIdentifierEnd(selector, index + 1)
  const identifier = selector.slice(index + 1, identifierEnd)
  result += shouldExcludeSelector(identifier) ? `.${identifier}` : `.${prefix}${identifier}`
  index = identifierEnd
  continue
}
// getPrefixedKey tail:
const prefixedKey = prefixSelectorClasses(key, prefix)
return /^[>+~]/.test(prefixedKey) && !prefixedKey.includes(",") ? ` ${prefixedKey}` : prefixedKey
```

**Flow:** keys are classified — `--x` → prefix the var name unless excluded; `@property --x` → run the value-string regex over the key; other `@` keys untouched; else scan as a selector where only attribute-depth-zero dots start class identifiers → string values get `var(--name)` references rewritten by `/--([a-zA-Z0-9_-]+)/g`; objects/arrays recurse; child-combinator-leading keys (`> + ~`, no comma) gain a leading space so Tailwind nesting stays valid.
**Invariant:** class-like text inside quotes, comments, escapes, or `[...]` must not be prefixed (test case "class-like text in attributes, strings, comments, and escapes"); `prefix === ""` short-circuits keys and `prefix === 0` no-ops values (sentinel distinction pinned by test line 356); exclusions are name-prefix based, not substring based.
**Probe:** `packages/daisyui/functions/addPrefix.test.js:6-367` — 40+ table cases including nested pseudo-functions (`.btn:where(:checked:not(.filter [type='radio'].btn))`), comma-separated ampersand lists, `@property`, and custom excluded prefixes; executed GREEN at pin (part of the 56-pass run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-daisyui", query: "addPrefix prefixSelectorClasses prefix variable", limit: 10 });
```
Executed this pass via graph rows for `addPrefix` (198–204, fan-in hotspot in bundle) plus full source/test reads.

## Verdict
Adopt the scanner's state set (quote/comment/escape/bracket) and the exclusion-list design as pure contracts. Adapt the specific excluded names/prefixes to your library's token vocabulary. Omit daisyUI's hardcoded `tw*` carve-out if your host doesn't emit `--tw-*` internals.
