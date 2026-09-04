<!-- capsule-v2 -->
# Operational-vs-programmer error split — how does a process decide whether an unknown error means "handle it" or "restart me"?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What is the canonical two-kind error taxonomy and the crash-decision predicate that a porter must reproduce when building an app-wide error handler?

## Two-kind taxonomy with a boolean trust flag
**Path/Symbol:** `sections/errorhandling/operationalvsprogrammererror.md` (whole doc, explainer :5, AppError marking :13-27) + `sections/errorhandling/shuttingtheprocess.md` (`isTrustedError` :29/:68).
**Signature:** `AppError(commonType, description, isOperational)`; `handler.isTrustedError(error) → boolean`; `process.on('uncaughtException', error => { handleError(error); if (!isTrustedError(error)) process.exit(1); })`.
**Data Shape:** every thrown value carries `isOperational: true|false`. Operational = known situation, understood impact (invalid input, downstream 5xx, connection refused) → log + respond, stay up. Programmer/catastrophic = unknown state (undefined deref, pool leak, invariant break) → process is untrustworthy, exit(1) and let the restarter own recovery.

### Decisive source
```javascript
// shuttingtheprocess.md :15-18 — the crash decision is a single trust check
process.on('uncaughtException', (error) => {
  errorManagement.handler.handleError(error);
  if(!errorManagement.handler.isTrustedError(error))
    process.exit(1)
});
// operationalvsprogrammererror.md :53 — TS subclass restores prototype chain
Object.setPrototypeOf(this, new.target.prototype); // restore prototype chain
this.isOperational = isOperational;
```

**Flow:** throw site marks the error operational-or-not → central handler always logs/metrics it → `isTrustedError` reads ONLY the flag (`error.isOperational`, and for non-AppError values returns false = untrusted) → untrusted ⇒ `process.exit(1)`; restarter (Docker/K8s/systemd/PM2) supplies clean state.
**Invariant:** an unknown error must never be survived in-process — Node docs quote: there is "almost never any way to safely 'pick up where you left off'". Conversely a known operational error must NOT take down ~5000 online users. The flag, not the stack, decides.
**Probe:** no test runner upstream (docs-only repo). Deterministic probe (re-derived & byte-exact executed 2026-08-24): `grep -c 'isTrustedError' sections/errorhandling/shuttingtheprocess.md` = 4 AND `grep -c 'process.exit(1)' sections/errorhandling/shuttingtheprocess.md` = 2; Joyent "crash immediately" quote present in both files. ERRATUM: this capsule originally shipped the second anchor as `grep -c 'process.exit(1)' …` ≥ 2 — a literal `…` ellipsis path (grep: No such file or directory); never abbreviate file paths in probes.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "uncaughtException", "limit": 10}'
# resolves `sections/errorhandling/operationalvsprogrammererror.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the two-kind taxonomy + boolean trust flag as the universal error-handling skeleton (language-portable far beyond Node). Adapt the marker mechanism per language (TS needs `setPrototypeOf(this, new.target.prototype)` after `super()`; JS factory uses `Error.call(this)` + `captureStackTrace`). Omit the specific restarter choice (PM2 vs systemd vs K8s) — that is host infrastructure, see `uptime-ownership-ladder` capsule.
