<!-- capsule-v2 -->
# Native-over-userland performance rule & lint gate — when may you pull lodash, and what catches violations?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What's the measured cost of userland utility methods over V8 natives, and how is the rule enforced mechanically?

## ~50% aggregate penalty (146% mean); ESLint you-dont-need-lodash-underscore plugin flags replacements
**Path/Symbol:** `sections/performance/nativeoverutil.md` (:7 premise, :8 method list + gain link, :16 mean benchmark figure), (:21-34 benchmark suite pattern), (:48-57 plugin config), (:61-67 _.map flagging example).
**Signature:** `.eslintrc`: `"extends": ["plugin:you-dont-need-lodash-underscore/compatible"]`; flagged: `_.map([0,1,2], x => ...)` → suggests native `[0,1,2].map(...)`.
**Data Shape:** covered methods incl. Array.concat/fill/filter/map, (Array|String).indexOf; benchmark mean: Lodash methods take on average 146.23% more time than V8 equivalents.

### Decisive source
```text
# nativeoverutil.md :7-8
Sometimes, using native methods is better than requiring _lodash_ or
_underscore_ because those libraries can lead to performance loss or take up
more space than needed. The performance using native methods result in an
overall ~50% gain which includes the following methods:
`Array.concat`, `Array.fill`, `Array.filter`, `Array.map`,
`(Array|String).indexOf`, ...
```

**Flow:** code review/CI lints with the YDNLU plugin → compatible calls get autofix-style suggestions to natives → only genuinely missing functionality (deep-equality, debouncing, chunking) keeps a dependency.
**Invariant:** the rule is conditional ("sometimes" :7) — it targets methods V8 already covers, not all of lodash; bundle-size and perf both improve when dropped. Enforcement is mechanical (lint plugin), not stylistic preference. Same enforcement philosophy as `eval-family-ban`/`static-require-discipline`: convert the practice into a detector.
**Probe:** no runner upstream. Deterministic probe: `grep -c '50% gain' sections/performance/nativeoverutil.md` >= 1 && `grep -c 'you-dont-need-lodash-underscore' sections/performance/nativeoverutil.md` >= 2.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "you-dont-need-lodash", limit: 5 });`

## Verdict
Adopt the lint-gated native-first default and the conditional escape hatch. Adapt to your runtime floor (the ES5/ES6 coverage assumption predates modern baselines where even more lodash is redundant). Omit benchmark binaries/spreadsheets.
