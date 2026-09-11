<!-- capsule-v2 -->
# TLS termination shape — https.createServer(cert pair) or proxy-side SSL; both are first-class

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Where does encryption terminate, and what's the minimal in-Node config?

## Node-native: cert+key files into https module; proxy alternative equally blessed
**Path/Symbol:** `sections/security/secureserver.md` (:7-10 options framing, example :14-26).
**Signature:** `https.createServer({ cert: fs.readFileSync('./sslcert/fullchain.pem'), key: fs.readFileSync('./sslcert/privkey.pem') }, app).listen(443)`.
**Data Shape:** fullchain (cert chain) + privkey pair from Let'sEncrypt-class CA; same config expressible on nginx/HAProxy instead.

### Decisive source
```javascript
// secureserver.md :20-25
const options = {
    // The path should be changed accordingly to your setup
    cert: fs.readFileSync('./sslcert/fullchain.pem'),
    key: fs.readFileSync('./sslcert/privkey.pem')
};
https.createServer(options, app).listen(443);
```

**Flow:** free-CA economics removed the excuse (:7-9) → either Node terminates TLS itself via the core `https` module, or the reverse proxy does it and speaks plain HTTP to the app on a private network. Both positions appear in this doc AND `non-root-execution-contract` (proxy owns 80/443) — pick per topology, never run plain HTTP toward the internet.
**Invariant:** TLS at ONE hop is not end-to-end — if the proxy terminates, internal hops still need network-level trust. The header layer (`security-header-matrix`: HSTS) only means anything once TLS actually terminates for real users; Expect-CT/HSTS presuppose this capsule is solved.
**Probe:** no runner upstream. Deterministic probe: `grep -cE 'createServer|Let.sEncrypt' sections/security/secureserver.md` >= 2.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "createServer", "limit": 10}'
# resolves `sections/security/secureserver.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt proxy-termination as default behind orchestrators; direct `https.createServer` for single-box deploys. Adapt cert provisioning automation freely. Omit self-signed setups outside dev.
