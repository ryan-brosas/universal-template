<!-- capsule-v2 -->
# Production-readiness meta checklist — which development habits does upstream tie directly to production stability?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What cross-cutting code practices does the repo mandate before code ships, and where does each point for depth?

## Twelve-factor anchor + named-function profiling + CI sync-API detection + test-like-production + JSON logs w/ transaction-id
**Path/Symbol:** `sections/production/productioncode.md` (:9-17 nine-bullet list).
**Signature:** bullets — twelve-factor familiarity; statelessness (→ own capsule); cache without fail-on-mismatch; memory gauging in dev flow (memwatch-class); NAMED functions (profilers report per method name); CI lint (`--trace-sync-io` for synchronous-API usage in async paths); JSON logs carrying transaction-id; test-like-production via Docker-Compose WITHOUT env if/else branches; deliberate error-management strategy.
**Data Shape:** this doc is a HUB — each bullet delegates depth to its own practice doc.

### Decisive source
```text
# productioncode.md :13-16 — the least-obvious three
- Name functions – Minimize the usage of anonymous functions (i.e. inline
callback) as a typical memory profiler will provide memory usage per method name
- Use CI tools – ...use ESLint to detect reference errors and undefined
variables. Use –trace-sync-io to identify code that uses synchronous APIs
(instead of the async version)
- Test like production - Make developers machine quite close to the
production infrastructure (e.g., with Docker-Compose). Avoid if/else clauses
in testing that check if we're in testing environment but rather run the same
code always
```

**Flow:** each bullet is enforced at a different lifecycle stage — design (12-factor, stateless), coding (named functions, scoped variables), CI (lint + trace-sync-io), logging (JSON + transaction-id → pairs with `transaction-id-correlation`), testing (prod-parity infra, no env branches).
**Invariant:** anonymous callbacks make heap profiles unreadable ("memory usage per method name" is the whole reason); env-if/else in tests creates code paths production never exercises — the exact class of bug prod-parity testing exists to kill. Error handling is called "the Achilles' heel of Node.js production sites" — strategy-setting is mandated, not optional (:17).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'trace-sync-io' sections/production/productioncode.md` >= 1 && `grep -c 'Name functions' sections/production/productioncode.md` >= 1 && `grep -cF 'if/else clauses' sections/production/productioncode.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "productioncode", limit: 5 });`

## Verdict
Adopt as a pre-ship review rubric (each bullet maps to one of this foundation's capsules or an explicit sibling). Adapt tooling names. Omit nothing except the outbound personal-blog link.
