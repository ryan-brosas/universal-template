<!-- capsule-v2 -->
# CRUD round-trip probe — what request sequence proves a deployment is actually functional, and which assertions catch silent misconfiguration?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** What minimal authenticated exercise proves a Nexus deployment accepts writes and serves reads under the new credentials?

## Five-assertion live smoke
**Path/Symbol:** `scripts/smoke.py:3-15` (whole script; single-expression-per-line style with `;` chains).
**Signature:** env-driven: `BASE_URL`, `ADMIN_PASSWORD` (required, KeyError if missing), `ACCEPT_NEXUS_EULA` (optional). One `uuid.uuid4().hex[:10]`-suffixed repo name per run (`railway-<10 hex>`) so re-runs never collide.
**Data Shape:** raw hosted repo payload: `{'name','online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True,'writePolicy':'ALLOW_ONCE'},'cleanup':None,'component':{'proprietaryComponents':False},'raw':{'contentDisposition':'ATTACHMENT'}}`. POST expects 201; PUT artifact expects 200/201/204 (version-tolerant); GET-back asserts status 200 AND byte-exact body equality (`get.content==content`) — not just a 200.

### Decisive source
```python
name='railway-'+uuid.uuid4().hex[:10];payload={'name':name,'online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True,'writePolicy':'ALLOW_ONCE'},'cleanup':None,'component':{'proprietaryComponents':False},'raw':{'contentDisposition':'ATTACHMENT'}};r=requests.post(b+'/service/rest/v1/repositories/raw/hosted',auth=('admin',pw),json=payload,timeout=60);assert r.status_code==201,r.text
content=b'Nexus Railway artifact probe';u=b+'/repository/'+name+'/probe.txt';put=requests.put(u,auth=('admin',pw),data=content,headers={'Content-Type':'text/plain'},timeout=60);assert put.status_code in (200,201,204),put.text;get=requests.get(u,auth=('admin',pw),timeout=30);assert get.status_code==200 and get.content==content
```

**Flow:** health (status 200) → anonymous blocked (401/403) → wrong-password rejected → correct credentials authorized (200) → EULA gate → create unique raw-hosted repo → PUT probe bytes → GET back and compare BYTES. Each assert carries a failure message (`r.text`) so diagnostics survive the exception.
**Invariant:** "server responds" ≠ "deployment works" — only a full write+read-back of known bytes through a freshly created repository proves the storage stack end-to-end. The unique-name-per-run convention makes the probe idempotent-safe to rerun against a long-lived instance.
**Probe:** self-probing by design; static twin in `tests/static.mjs` (EULA opt-in marker present). Runtime caveat recorded (needs live BASE_URL + ADMIN_PASSWORD).

## Get live surrounding code
**Retrieve:** BM25 search_graph returns total:0 for payload tokens (source text is not node-indexed on this config-shaped graph — verified live this pass); use line-exact search_code:
```
codebase-memory-mcp search_code {"project":"railway-template-nexus3","pattern":"ALLOW_ONCE","limit":5}
```
→ EXECUTED this pass: Variable `scripts.smoke.name` in scripts/smoke.py lines 13-13, match at `"13"` (the repo-create line).

## Verdict
Adopt the five-stage ladder (health → anon-block → bad-auth-reject → good-auth-accept → byte-exact CRUD round-trip) as the canonical post-deploy verification for any artifact/service deployment. Adapt repo payload per product API. Omit nothing behavioral.
