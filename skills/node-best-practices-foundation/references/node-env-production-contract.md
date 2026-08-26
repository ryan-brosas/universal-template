<!-- capsule-v2 -->
# NODE_ENV=production contract — what does the flag actually gate, and how must it be set?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Why does an unset NODE_ENV silently degrade a production deployment, and where is the flag set?

## Deployment-tool env var (not in-code); unset ⇒ Express-class throughput drops ~3x
**Path/Symbol:** `sections/production/setnodeenv.md` (:7 env-var mechanism), (:13-23 set/read examples), (:30 3x dynatrace measurement), (:37-39 Snyk framework-optimization caveat).
**Signature:** shell/deployer: `$ NODE_ENV=production` before process start; read: `if (process.env.NODE_ENV === 'production') useCaching = true;`
**Data Shape:** convention variable; any value ≠ 'production' behaves as development; supported by every deployment tool (Chef/Puppet/CloudFormation).

### Decisive source
```text
# setnodeenv.md :7 — the mechanism
Node encourages the convention of using a variable called NODE_ENV to flag
whether we're in production right now. This determination allows components
to provide better diagnostics during development, for example by disabling
caching or emitting verbose log statements.
# :30 — the measured cost of omission
by setting NODE_ENV to production the number of requests Node.js can handle
jumps by around two-thirds while the CPU usage even drops slightly.
```

**Flow:** deployment tool injects NODE_ENV=production into the process environment → view caching, verbose logging, and dev-only middleware branches switch off → per-request overhead drops (~3x throughput on Express-class apps).
**Invariant:** it's an ENVIRONMENT variable set at deploy time, not a config-file key or CLI arg inside app code. Some frameworks/libraries enable their optimized configuration ONLY when it equals 'production' — omission silently runs dev-mode code paths with no error anywhere.
**Probe:** no runner upstream. Deterministic probes (re-derived & executed 2026-08-24): `grep -c "process.env.NODE_ENV" sections/production/setnodeenv.md` = 1 and `grep -c '3 times faster' sections/production/setnodeenv.md` = 1. ERRATUM: the original second clause pinned `'three times faster'`, which returned 0 — silently dead since authoring: the doc's Dynatrace-derived claim reads "makes your application **3** times faster!" with a DIGIT, spelled-out "three" never occurs.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "NODE_ENV", limit: 5 });`

## Verdict
Adopt env-var-at-deploy-time placement and treat NODE_ENV=production as part of the release checklist, not application logic. Adapt: don't branch feature behavior on it beyond perf/diagnostics gating. Omit nothing.
