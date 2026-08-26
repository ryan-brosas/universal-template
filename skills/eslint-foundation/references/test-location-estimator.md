<!-- capsule-v2 -->
# Stack-rebuilt failure locations — how do you point test failures at the exact source line of a declaratively-defined case?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the tester rewrite thrown errors into "roughly at valid[3]" stack frames that name the user's own source file and line?

## getInvocationLocation + buildLazyTestLocationEstimator
**Path/Symbol:** `lib/rule-tester/rule-tester.js:getInvocationLocation` (:662–679), `buildLazyTestLocationEstimator(invoker)` (:686–845).
**Signature:** `getInvocationLocation(relative?) → {sourceFile, sourceLine, sourceColumn}`; `estimateTestLocation(key) → "file:line"` for keys `root`, `valid`, `invalid`, `valid[i]`, `invalid[i]`, `invalid[i].errors[j]`.
**Data Shape:** location capture overrides `Error.prepareStackTrace` TEMPORARILY (`Error.captureStackTrace(dummy, relative)` for Bun + forced `dummyObject.stack` read for Node) and restores the previous prepareStackTrace in a disciplined sequence.

### Decisive source
```js
// lazy parse of the CALLER's source file, once:
content = readFileSync(sourceFile).split("\n").slice(sourceLine - 1);
content.map(l => l.trim().replace(/\s*\/\/.*$(?<!,)/u, "")); // strip trailing comments NOT ending in comma
const validStartIndex = content.findIndex(l => /\bvalid\s*:/u.test(l));
const invalidStartIndex = content.findIndex(l => /\binvalid\s*:/u.test(l));
// brace-depth walk: objectDepth>0 tracks `{`/`}`; record lines with `code:` at depth ≤1,
// invalid error objects keyed by `errors:`-starting lines; per-case error indexes by depth-1 scan.
```

**Flow:** on first miss, re-reads the tester's OWN file from the captured invocation point → regex-locates `valid:`/`invalid:` blocks → brace-depth scans to map each array index (and each `errors[]` entry inside invalid cases) to a line number → caches all keys → every later lookup is a Map hit. On failure the runner string-replaces the first stack frame with synthetic frames: `roughly at RuleTester.run.invalid[i].error[j]` / `.invalid[i]` / `.invalid` / `at RuleTester.run`, tagging `err.scenarioType/scenarioIndex/errorIndex`.
**Invariant:** estimation is BEST-EFFORT by design — unreadable sources (eval, data: URLs, vm scripts) degrade to `"unknown source"`, never throw; the comment-stripping regex deliberately spares trailing commas (`(?<!,)`) because a stripped comma would break the brace-depth grammar. Frames are prefixed "roughly at" to keep honest about heuristics. This whole subsystem exists because Mocha/Vitest otherwise report line numbers inside rule-tester.js, useless to rule authors.
**Probe:** `tests/lib/rule-tester/rule-tester.js` (:6734+ "error locations" describe — object/multi-line/eval cases :6803–7056, data-module :7057 & global-context :7086 unknown-source cases, suggestion-failure attribution :7356).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "buildLazyTestLocationEstimator getInvocationLocation estimateTestLocation", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rule-tester.rule-tester.buildLazyTestLocationEstimator" });
```

## Verdict
Adopt the pattern for any data-driven test harness whose failures would otherwise point into framework code; adapt the block-detection grammar to your DSL; omit if your runner already attributes cases natively.
