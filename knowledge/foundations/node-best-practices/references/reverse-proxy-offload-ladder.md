<!-- capsule-v2 -->
# Reverse-proxy offload ladder — which networking tasks must leave the Node process, and to where?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Why is serving static content/gzip/SSL from Express a performance failure, and what's the ranked offload topology?

## Node executes short async tasks; static files/gzip/TLS belong to proxy, cloud storage, or CDN
**Path/Symbol:** `sections/production/delegatetoproxy.md` (:7 single-thread kill + nginx/HAProxy), (:11-40 nginx config with gzip levels, upstream keepalive 64, SSL pair, static location regex), `sections/production/frontendout.md` (:7 rationale, :9-13 two-form ladder, :17-35 config twin).
**Signature:** nginx `gzip on; gzip_comp_level 6; gzip_vary on;` / `upstream myApplication { server 127.0.0.1:3000; server 127.0.0.1:3001; keepalive 64; }` / `location ~ ^/(images/|...|static/|robots.txt)  { root .../public; access_log off; expires max; }`
**Data Shape:** offload targets ranked — (1) reverse proxy adjacent to app (app deploys but doesn't serve statics), (2) cloud storage S3/Azure Blob (app neither deploys nor serves), plus CDN in front.

### Decisive source
```text
# delegatetoproxy.md :7
It's very tempting to cargo-cult Express and use its rich middleware offering
for networking related tasks like serving static files, gzip encoding,
throttling requests, SSL termination, etc. This is a performance kill due to
its single threaded model...
# frontendout.md :43 — the sendFile trap
don't do this in production, because this function has to read from the file
system for every file request... Note that res.sendFile() is not implemented
with the sendfile system call
```

**Flow:** browser → proxy terminates TLS + gzips + serves static regex locations directly (access_log off, expires max) → only dynamic routes reach the upstream Node pool over keepalive'd connections.
**Invariant:** Node's execution model is optimized for SHORT tasks and async IO — a burst of static-file service starves the event loop and drops connections ("connections are dropped, assets stop being served or... your server crashes" :47). Never let `res.sendFile()`-per-request reach production.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'keepalive 64' sections/production/delegatetoproxy.md` = 1 && `grep -c 'gzip on' sections/production/frontendout.md` >= 1 && `grep -c 'res.sendFile()' sections/production/frontendout.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "delegatetoproxy", limit: 5 });`

## Verdict
Adopt the task split (TLS/static/gzip/throttle → infra layer) and both offload forms. Adapt proxy choice (nginx/HAProxy/cloud LB) and CDN topology. Omit the doc-era sillyfacesociety config verbatim — keep gzip level, upstream keepalive, and static-location shape as starting parameters.
