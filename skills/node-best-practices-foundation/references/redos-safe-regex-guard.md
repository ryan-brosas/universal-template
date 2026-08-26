<!-- capsule-v2 -->
# ReDoS guard — nested repetition is the bomb; safe-regex gate or validator library

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which regex shapes freeze the event loop, and how do you detect them before deploy?

## safe-regex check + validator.js substitution; the vulnerable grammar is repetition-over-repetition
**Path/Symbol:** `sections/security/regex.md` (risk statement :3-6, OWASP examples :8-10, probe example :16-26, Tal definition :30-33).
**Signature:** `saferegex(pattern): boolean` (false = vulnerable); replacement: `validator.isEmail(s)` etc.
**Data Shape:** known-vulnerable shapes: `(a|aa)+`, `([a-zA-Z]+)*` — a quantifier applied to an expression that itself can match the same text multiple ways.

### Decisive source
```javascript
// regex.md :17-25
const saferegex = require('safe-regex');
const emailRegex = /^([a-zA-Z0-9])(([\-.]|[_]+)?([a-zA-Z0-9]+))*(@){1}...$/;
console.log(saferegex(emailRegex)); // false => vulnerable to redos attacks
console.log(validator.isEmail('liran.tal@gmail.com')); // instead of the regex
```

**Flow:** single-threaded event loop means one CPU-bound backtracking match blocks EVERY request (:5) → attacker submits crafted non-matching suffix ("a string ... composed of a suffix of a valid matching pattern plus characters that aren't matching", :33) → engine explores exponential backtrack paths → application unresponsive. Defense: run candidate patterns through safe-regex (static star-height analysis) in CI; replace hot-path validation with purpose-built validators.
**Invariant:** the danger is data-dependent, so unit tests with normal inputs pass forever; only adversarial suffixes trigger it. The doc's own example email regex FAILS the safe-regex check (:20-21) — "looks fine in prod" patterns are exactly the risk.
**Probe:** no runner upstream. Deterministic probe: `grep -c '(a|aa)+\|safe-regex' sections/security/regex.md` >= 2.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "safe-regex", "limit": 10}'
# resolves `sections/security/regex.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt safe-regex as a lint/CI gate on literal patterns. Adapt: pair with `commonsecurity-random-compare`'s eslint-plugin-security rules (`detect-non-literal-regexp` covers dynamic construction). Omit hand-auditing — tooling exists precisely because human review misses nested quantifiers.
