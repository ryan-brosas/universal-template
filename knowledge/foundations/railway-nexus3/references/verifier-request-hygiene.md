<!-- capsule-v2 -->
# Verifier request hygiene — how should a post-deploy smoke script shape its HTTP requests so operator config variance and a slow JVM cannot produce false failures?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3` (generation 2026-08-25T08:42:38Z, all cited paths metadata_match). **Question:** What request-level hygiene does the live verifier apply to base URL, per-request timeouts, and its success output so it measures the DEPLOYMENT rather than its own assumptions?

## Normalized base + timeout classes matched to operation cost
**Path/Symbol:** `scripts/smoke.py:3` (base normalization), `scripts/smoke.py:3,13,14` (60 s class), `scripts/smoke.py:4,5,6,7,12,14` (30 s class), `scripts/smoke.py:15` (success marker). Graph nodes: EnvVar `__env__BASE_URL`, Variable `scripts.smoke.b`, module `railway-template-nexus3.scripts.smoke`.
**Signature:** `b=os.environ['BASE_URL'].rstrip('/')`; every request is then built as string concat `b+'/service/rest/v1/...'` / `b+'/repository/'+name+'/probe.txt'`; every `requests.get/post/put` carries an explicit `timeout=`.
**Data Shape:** Two timeout classes over the nine requests: **60 s** for requests that can land while the JVM is still warming or that trigger storage work — the initial status probe (`:3`), repository create POST (`:13`), content PUT (`:14`); **30 s** for everything else — negative probes (`:4,:5`), authed read (`:6`), EULA GET/POST (`:7,:12`), artifact GET-back (`:14`). Success line prints `'Nexus smoke checks passed',name` where `name` is the created repo.

### Decisive source
```python
b=os.environ['BASE_URL'].rstrip('/');pw=os.environ['ADMIN_PASSWORD'];status=requests.get(b+'/service/rest/v1/status',timeout=60);assert status.status_code==200
...
r=requests.post(b+'/service/rest/v1/repositories/raw/hosted',auth=('admin',pw),json=payload,timeout=60);assert r.status_code==201,r.text
content=b'Nexus Railway artifact probe';u=b+'/repository/'+name+'/probe.txt';put=requests.put(u,auth=('admin',pw),data=content,...,timeout=60);...;get=requests.get(u,auth=('admin',pw),timeout=30);assert get.status_code==200 and get.content==content
print('Nexus smoke checks passed',name)
```
(`scripts/smoke.py:3,13,14,15` VERBATIM at pin; elided middle = auth ladder + EULA gate at 30 s, both covered by `smoke-crud-roundtrip` / `eula-consent-gate`.)

**Flow:** verifier starts from an operator-supplied `BASE_URL` → trailing slash stripped ONCE so every join yields exactly one `/` regardless of config style → cheap fast-failing reads prove reachability/auth before slow writes run → only then do the storage-side operations execute under their longer budget → success output names the probe repository so the artifact can be located and deleted.
**Invariant:** a verifier must never fail because of ITS OWN request shaping. Three sub-contracts: (1) base normalization happens once, before any request — a trailing-slash `BASE_URL` would otherwise double-slash every path; (2) no request may omit `timeout=` (requests' default is wait-forever — one hung socket stalls the whole verification); (3) budgets follow operation cost, not symmetry: warmup-sensitive/storage-heavy calls get 2× the read budget, mirroring `platform-healthcheck-contract`'s "the JVM is slow during boot" premise from the platform side into the verifier side.
**Probe:** deterministic pins executed this pass at pin `18e177a6`: `grep -c "rstrip('/')" scripts/smoke.py` = 1; `grep -c 'timeout=30' scripts/smoke.py` = 6; `grep -c 'timeout=60' scripts/smoke.py` = 3; `grep -Ec 'requests\.(get|post|put)\(' scripts/smoke.py` = 8 request-BEARING lines (:14 carries two calls → nine calls total, and the 6+3=9 timeout literals prove every call is timed). Direct test twin: `tests/static.mjs` pins the EULA env literal in this same file (rc=0 observed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "BASE_URL environment variable smoke", limit: 10 });
```
→ resolves EnvVar `__env__BASE_URL`; module source via `get_code_snippet("railway-template-nexus3.scripts.smoke")` verified byte-equal to checkout this pass (check_index_coverage: scripts/smoke.py `no_recorded_issue`, metadata_match @ gen 2026-08-25T08:42:38Z).

## Verdict
Adopt normalize-once base handling, mandatory explicit timeouts, and cost-classed budgets for any post-deploy verifier. Adapt class boundaries to the target's measured cold-start (a faster service can use 30/10). Omit nothing — the three sub-contracts are independent; dropping any reintroduces a false-failure mode.
