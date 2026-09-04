<!-- capsule-v2 -->
# `.each`/`.for` title templating — how are `%s`-style placeholders, `$key` property interpolation, and tagged-template case tables rendered into test names?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** How does a single template string become N distinct, collision-free, human-readable test titles for arbitrary case shapes (tuples, scalars, objects, tagged-template rows) without executing user code?

## `formatTitle` + `formatTemplateString` in the collector tail
**Path/Symbol:** `packages/vitest/src/runtime/runner/suite.ts:formatTitle` (997–1063), `handleRegexMatch` (1066–1083), `formatTemplateString` (1085–1101), `formatName` (989–995); drivers `createTaskCollector.taskFn.each/.for` (744–838).
**Signature:** `formatTitle(template: string, items: any[], idx: number): string`; `formatTemplateString(cases: any[], args: any[]): any[]` (tagged-template arrays).
**Data Shape:** items = per-case payload already normalized (`Array.isArray(i) ? i : [i]`); reads `runner.config.taskTitleValueFormatTruncate`; output is a plain string used as the task name.

### Decisive source
```ts
function formatTitle(template: string, items: any[], idx: number) {
  if (template.includes('%#') || template.includes('%$')) {   // index placeholders
    template = template
      .replace(/%%/g, '__vitest_escaped_%__')                 // sentinel protects %%
      .replace(/%#/g, `${idx}`)                               // 0-based case index
      .replace(/%\$/g, `${idx + 1}`)                          // 1-based
      .replace(/__vitest_escaped_%__/g, '%%')
  }
  const count = template.split('%').length - 1                // placeholder budget
  if (template.includes('%f')) {
    const placeholders = template.match(/%f/g) || []
    placeholders.forEach((_, i) => {
      if (isNegativeNaN(items[i]) || Object.is(items[i], -0)) {
        let occurrence = 0                                    // re-sign only the i-th %f
        template = template.replace(/%f/g, (match) =>
          occurrence++ === i ? '-%f' : match)
      }
    })
  }
  const inspectOptions = { truncate: runner.config.taskTitleValueFormatTruncate }
  const isObjectItem = isObject(items[0])
  function formatAttribute(s: string) {                       // $key / $0 interpolation
    return s.replace(/\$([$\p{ID_Continue}.]+)/gu, (_, key) => {
      const isArrayKey = /^\d+$/.test(key)
      if (!isObjectItem && !isArrayKey) return `$${key}`      // non-object cases keep literal
      const arrayElement = isArrayKey ? objectAttr(items, key) : undefined
      const value = isObjectItem ? objectAttr(items[0], key, arrayElement) : arrayElement
      if (typeof value === 'string')
        return truncateString(value, inspectOptions.truncate) // strings print unquoted
      return inspect(value, inspectOptions)
    })
  }
  let output = ''; let i = 0
  handleRegexMatch(template, formatRegExp,
    match => { if (i < count) output += format([match[0], items[i++]], inspectOptions); else output += match[0] },
    nonMatch => { output += formatAttribute(nonMatch) })
  return output
}
```
Tagged-template table → objects:
```ts
const header = cases.join('').trim().replace(/ /g, '').split('\n').map(i => i.split('|'))[0]
for (let i = 0; i < Math.floor(args.length / header.length); i++) {
  const oneCase = {}; for (let j = 0; j < header.length; j++) oneCase[header[j]] = args[i * header.length + j]
  res.push(oneCase)
}
```

**Flow:** `.each(cases)` normalizes every case to an array → `arrayOnlyCases = cases.every(Array.isArray)` decides handler arity (`handler(...items)` spread vs `handler(i)` whole-payload) → per case, `formatName` fixes the raw name once, then `formatTitle` renders index placeholders → `%f` negative-zero re-signing → single linear pass where `%`-placeholders consume `items[i++]` positionally and every other segment gets `$key` attribute substitution → `.each` with a tagged template first folds `args` into `{header: value}` row objects via `formatTemplateString`. `.for` differs: it always passes the raw item as first arg plus a fixture-aware ctx wrapper.
**Invariant:** (1) extra `%` placeholders beyond available items stay literal (the `i < count` guard); (2) `%%` survives both index replacement AND positional formatting via the sentinel round-trip; (3) `-0`/-NaN get a visible sign because `util.format('%f')` would drop it; (4) `$key` works on object cases and numeric-array keys on tuple cases, everything else stays literal; (5) trailing partial rows of a tagged-template table are silently dropped (`Math.floor`); (6) unicode headers work because the key class is `\p{ID_Continue}`.

**Probe:** `test/unit/test/each.test.ts` (248 lines: tuple/object/scalar cases, `%s`+`%i`, nested `describe.each`, `$a/$b` object interpolation); `test/e2e/test/each-non-ascii-placeholders.test.ts` pins the exact titles `returns 5 given 1` / `returns 10 given 2` for a `时间戳 | 结果` table. Caveat: e2e needs installed deps; source read at pinned HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "suite collector mode skip only todo allowOnly", limit: 15 });
// observed: createSuiteCollector/createTaskCollector/formatTitle/formatTemplateString/
// handleRegexMatch all grouped under vitest.packages.vitest.src.runtime.runner.suite (lines above).
```

## Verdict
Adopt the two-layer grammar (positional `%` consumed left-to-right + declarative `$key` attributes) with the sentinel escape trick and the negative-sign fix. Adapt the formatter behind `%` (vitest uses its own pretty-format `format`) and the truncate knob. Omit the fixture-aware `.for` ctx plumbing unless your host has fixtures.
