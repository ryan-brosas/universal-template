<!-- capsule-v2 -->
# Error-detail suppression contract — production responses carry status codes, not stacks

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What does Express leak by default on unhandled errors, and what's the minimal production handler?

## Custom terminal error-handler renders message + empty error object
**Path/Symbol:** `sections/security/hideerrors.md` (:3-7 default behavior, example :11-21).
**Signature:** four-arg middleware `app.use((err, req, res, next) => { res.status(err.status || 500); res.render('error', { message: err.message, error: {} }) })`.
**Data Shape:** leaked material when unhandled: server file paths, third-party module names, internal workflow details via stack trace.

### Decisive source
```javascript
// hideerrors.md :12-20 — production error handler
app.use((err, req, res, next) => {
    res.status(err.status || 500);
    res.render('error', {
        message: err.message,
        error: {}        // <- deliberately EMPTY: no stack reaches the client
    });
});
```

**Flow:** error passed to `next()` with no custom handler ⇒ built-in Express handler writes THE STACK TRACE to the client (:7); `NODE_ENV=production` suppresses only the trace, leaving status-only — but relying on env-var correctness alone is fragile, so an explicit final-position handler pins the contract.
**Invariant:** the empty `error: {}` is the whole point — template code that forwards `err` "just for debugging" reintroduces the leak. Handler must be registered LAST (built-in one sits at stack end, :6). Pair with the error-handling section capsules (`operational-vs-programmer-split`, centralized handler): this capsule governs the CLIENT-FACING projection; internal logging keeps full detail.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'error: {}' sections/security/hideerrors.md` >= 1 && `grep -c 'stack trace' sections/security/hideerrors.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "stack trace", "limit": 10}'
# resolves `sections/security/hideerrors.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the explicit terminal-handler pattern in every Express service regardless of NODE_ENV discipline. Adapt rendering layer freely. Omit nothing — this is a ~10-line contract where omission IS the vulnerability.
