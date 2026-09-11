<!-- capsule-v2 -->
# Static require discipline + lint security ruleset — dynamic module paths and their detector rules

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which "just parameterize it" refactorings become file-read primitives for attackers?

## Literal require/fs paths only when input-derived; eslint-plugin-security names each pattern
**Path/Symbol:** `sections/security/safemoduleloading.md` (:9-15 example) + `sections/security/lintrules.md` (rule inventory :11-35).
**Signature:** banned: `require(variablePath)`, `fs.readFile(userPath)` with request-derived values; required: literal specifiers (`require('./helpers/upload')`).
**Data Shape:** detector vocabulary: `detect-pseudoRandomBytes`, `detect-non-literal-fs-filename`, `detect-eval-with-expression`, `detect-non-literal-regexp`.

### Decisive source
```javascript
// safemoduleloading.md :10-14 — the whole contract
// insecure, as helperPath variable may have been modified by user input
const badWayToRequireUploadHelpers = require(helperPath);
// secure
const uploadHelpers = require('./helpers/upload');

// lintrules.md :19-21 — the fs twin
const path = req.body.userinput;
fs.readFile(path);
```

**Flow:** dynamic require resolves ANY reachable file (node_modules included) as code and executes it; dynamic fs paths read arbitrary files — both turn "config flexibility" into arbitrary-code/file disclosure. The rule extends beyond modules: any sensitive resource accessed via request-originated variables (:5).
**Invariant:** the fix is structural, not sanitization: make the mapping EXPLICIT (whitelist object of allowed names→modules) so no attacker string ever reaches the resolver. Lint enforcement exists because these patterns look like normal code in review — `detect-non-literal-fs-filename` fires exactly the `fs.readFile(req.body.x)` shape reviewers skim past.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'require(helperPath)' sections/security/safemoduleloading.md` >= 1 && `grep -c 'detect-' sections/security/lintrules.md` >= 4.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "filename", "limit": 10}'
# resolves `sections/security/lintrules.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt static-specifier discipline + the four-rule security lint preset in every service template. Adapt allowlist mechanics per app. Omit nothing — the rule inventory doubles as the review checklist.
