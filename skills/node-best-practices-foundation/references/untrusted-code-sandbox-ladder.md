<!-- capsule-v2 -->
# Untrusted-code isolation ladder — dedicated process > serverless > vm-style library, weakest last

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** When you must execute code you didn't write (plugins, loaders), how do you bound the blast radius?

## Three rungs: child process / FaaS / sandbox library — each buys more isolation at more cost
**Path/Symbol:** `sections/security/sandbox.md` (rule :5, options :7-9, capability demo :13-33).
**Signature:** `new Sandbox().run(code, cb)` — errors return `'Syntax error'`, host access returns Null, infinite loops return `'Timeout'`.
**Data Shape:** isolation goals: resource limits, crash containment, information hiding ("fully isolated in terms of resources, crashes and the information we share", :5).

### Decisive source
```text
// sandbox.md :7-9 — the ladder with honest trade-offs
- a dedicated child process - quick information isolation but demand to tame
  the child process, limit its execution time and recover from errors
- a cloud serverless framework ticks all the sandbox requirements but
  deployment and invoking a FaaS function dynamically is not a walk in the park
- some npm libraries, like sandbox and vm2 allow execution of isolated code in
  1 single line of code. Though this latter option wins in simplicity it
  provides a limited protection
```

**Flow:** real systems accept dynamic code (webpack loaders are the doc's example, :5) → malicious plugin must be prevented from reading host state, hogging CPU, or crashing the parent. Rung choice = threat model × ops budget: child processes need timeout+recovery plumbing; serverless gives hard tenancy but awkward dynamic invocation; in-process VM libraries are one line but explicitly "limited protection".
**Invariant:** rule zero comes FIRST: "one should run his own JavaScript files only" (:5) — the ladder exists because reality violates the rule, not because the rule is optional. The demo proves containment semantics matter: `process.platform` → Null and `while(true){}` → Timeout are CONTRACTS to verify, not assume.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'vm2\|Timeout' sections/security/sandbox.md` >= 2.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "execution", "limit": 10}'
# resolves `sections/security/sandbox.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the ladder ordering for any plugin/loader surface; treat vm2-class libraries as defense-in-depth only, never the sole boundary against hostile code. Adapt to containers/gVisor equivalents on your platform. Omit nothing — the trade-off table IS the content.
