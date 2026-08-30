<!-- capsule-v2 -->
# Ephemeral-port test bootstrap — how do you start the server in tests so parallel runners never collide?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What is the one-line trick that lets multiple test processes bind simultaneously?

## Port 0 in testing, explicit PORT in production
**Path/Symbol:** `sections/testingandquality/randomize-port.md` (explainer :3, code :9-22).
**Signature:** `const webServerPort = process.env.PORT ? process.env.PORT : 0;` then `expressApp.listen(webServerPort, ...)`. Port `0` = ephemeral: the OS allocates a free port.
**Data Shape:** input: `process.env.PORT` set in production (fixed), absent in tests (→ 0). Output: server bound to an OS-chosen port; test code never needs to know the number because the server object is resolved and used in-process.

### Decisive source
```javascript
// randomize-port.md :16-20
const webServerPort = process.env.PORT ? process.env.PORT : 0;
expressApp = express();
connection = expressApp.listen(webServerPort, () => {
  resolve(expressApp); // no port needed — tests use the in-process server
});
```

**Flow:** test runner spawns multiple worker processes → each boots its own server → each binds an OS-allocated ephemeral port → no collision. In production the same code path uses the fixed PORT env.
**Invariant:** never hard-code a fixed port in tests — "Specifying a fixed port will prevent two testing processes from running at the same time. Most of the modern test runners run with multiple processes by default" (README 4.12). In-process server startup also unlocks mocking/coverage that out-of-process testing can't.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'process.env.PORT ? process.env.PORT : 0' sections/testingandquality/randomize-port.md` = 1.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "process.env.PORT  process.env.PORT : 0", "limit": 10}'
# resolves `sections/testingandquality/randomize-port.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the PORT-env-or-zero pattern for any Node/Express-style server and any parallel test runner. Adapt env var name per host. Omit nothing — the zero-port idiom is the whole contract.
