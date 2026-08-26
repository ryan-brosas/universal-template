<!-- capsule-v2 -->
# npm-test template gate — what makes a repo with no runtime code still have a meaningful `npm test`, and why does it run in plain node?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** Why is the test harness wired as `"type":"module"` + zero-dependency ESM, and what does that choice buy?

## One-line package.json, one-file suite, zero deps
**Path/Symbol:** `package.json:1` (whole file), `tests/static.mjs:1` (whole suite).
**Signature:** `{"name":"railway-template-nexus3","version":"1.0.0","private":true,"type":"module","scripts":{"test":"node tests/static.mjs"}}`.
**Data Shape:** `private:true` (never publish); `"type":"module"` makes `.mjs`-style ESM import syntax legal in this package; single `test` script → standard `npm test` entry point.

### Decisive source
```json
{"name":"railway-template-nexus3","version":"1.0.0","private":true,"type":"module","scripts":{"test":"node tests/static.mjs"}}
```

**Flow:** CI or a reviewer runs `npm test` → node executes `tests/static.mjs` directly (no bundler, no transpile) → six regex pins over four files → exit code gates merges.
**Invariant:** the harness is deliberately DEPENDENCY-FREE: no devDependencies means `npm install` is a no-op, so the gate runs on ANY machine with bare node — including inside minimal CI images and offline air-gapped review environments. A porter who reaches for a test framework adds an install step and a supply-chain surface to guard exactly the literals the framework isn't needed to assert. `"type":"module"` + `.mjs` keep modern syntax without a build step; `private:true` prevents accidental publication of a template repo. The whole design point: a deployment template's correctness surface is its FILE TEXT, so its tests should be executable file-text assertions, not service integrations.
**Probe:** EXECUTED this pass: `node tests/static.mjs` rc=0 from repo root ("static template checks passed"); `grep -cF '"type":"module"' package.json` = 1; `grep -cF 'node tests/static.mjs' package.json` = 1; `grep -cF '"private":true' package.json` = 1.

## Get live surrounding code
**Retrieve:** line-exact search_code resolves the suite side; EXECUTED this pass:
```
codebase-memory-mcp search_code '{"project":"railway-template-nexus3","pattern":"static template checks passed","limit":5}'
```
→ Variable `tests.static.d` in tests/static.mjs lines 1-1, match at `"1"`. COVERAGE CAVEAT (verified live this pass): `package.json`'s TEXT is not reachable through search_code on this graph (`pattern:"module", file_pattern:"package.json"` → total:0) although its Module node exists — the `package.json` contract above is whole-file-source-confirmed by direct read, not graph-text-retrievable; re-check if the graph is rebuilt.

## Verdict
Adopt: wire template gates as zero-dependency `node <file>.mjs` under a standard `npm test` script with `private:true`; assert file-text invariants directly instead of importing a framework. Adapt assertion set per product's security surface. Omit nothing.
