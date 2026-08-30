<!-- capsule-v2 -->
# Maintenance endpoint — when does in-app ops tooling beat external monitoring, and what are its gates?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What justifies exposing heap dumps/REPL through the app itself, and which two controls must wrap it?

## Golden rule = external tools first; endpoint exists ONLY for Node/app-specific introspection; admin-gated + DDoS-target aware
**Path/Symbol:** `sections/production/createmaintenanceendpoint.md` (:7 role+golden rule+both gates), (:13-34 heapdump handler).
**Signature:** `router.get('/ops/heapdump', ...)` → `if (!isAuthorized(req)) return res.status(403).send(...)` → `logger.info('About to generate heapdump')` → `heapdump.writeSnapshot((err, filename) => {...})`.
**Data Shape:** privileged operations exposed over HTTP: heap snapshot write+read-back, memory-leak reports, direct REPL execution.

### Decisive source
```text
# createmaintenanceendpoint.md :7 — scope + both gates in one paragraph
The golden rule is using professional and external tools for monitoring and
maintaining the production... there are likely to be cases where the generic
tools will fail to extract information that is specific to Node or to your
app – for example, should you wish to generate a memory snapshot at the
moment GC completed a cycle... It is important to keep this endpoint private
and accessibly only by admins because it can become a target of a DDOS attack.
```

**Flow:** conventional DevOps tooling first → only when a tool CANNOT reach Node-specific state (GC-moment snapshot) does an in-app route get built → request hits authorization gate (403 on failure) → audit log BEFORE side effect → operation executes → result streamed to caller.
**Invariant:** two mandatory gates — admin-only authorization and awareness that the endpoint itself is a DDoS target (keep private/network-restricted). The golden rule bounds scope: never re-implement generic monitoring in-app.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'DDOS' sections/production/createmaintenanceendpoint.md` >= 1 && `grep -c heapdump sections/production/createmaintenanceendpoint.md` >= 3 && `grep -c 'golden rule' sections/production/createmaintenanceendpoint.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "heapdump", limit: 5 });`

## Verdict
Adopt the golden-rule scoping test and both gates for any ops route you do expose. Adapt the auth mechanism to your identity layer (the doc leaves isAuthorized as a stub). Omit the deprecated heapdump package API — modern equivalents: v8.getHeapSnapshot / inspector session.
