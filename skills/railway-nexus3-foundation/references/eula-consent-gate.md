<!-- capsule-v2 -->
# EULA consent gate — how does automation verify a deployment without accepting a legal agreement on the operator's behalf?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How does the smoke script check and — only with explicit operator opt-in — accept the Nexus Community Edition EULA, and what makes the refusal path correct?

## Read-check-ask-accept ladder
**Path/Symbol:** `scripts/smoke.py:7-12` (whole seam), env `ACCEPT_NEXUS_EULA` (`:9`, indexed as `__env__ACCEPT_NEXUS_EULA` in the graph).
**Signature:** `eula_state = requests.get(b+'/service/rest/v1/system/eula', auth=('admin',pw), timeout=30)`; acceptance `requests.post(..., json={'accepted':True,'disclaimer':disclaimer})` expecting HTTP 204.
**Data Shape:** GET returns JSON `{accepted: bool, ...}`. POST body requires BOTH the boolean AND the verbatim disclaimer string (quoting the EULA URL) — server-side 204 proves the pair. Opt-in is a string-compared env: `os.environ.get('ACCEPT_NEXUS_EULA')!='true'` → `raise SystemExit(...)` naming the EULA link.

### Decisive source
```python
if not eula_state.json().get('accepted',False):
    if os.environ.get('ACCEPT_NEXUS_EULA')!='true':
        raise SystemExit('Refusing to accept the Nexus Community Edition EULA automatically. Read https://links.sonatype.com/products/nxrm/ce-eula and set ACCEPT_NEXUS_EULA=true only if you accept it.')
    disclaimer='Use of Sonatype Nexus Repository - Community Edition is governed by the End User License Agreement at https://links.sonatype.com/products/nxrm/ce-eula. By returning the value from 'accepted:false' to 'accepted:true', you acknowledge that you have read and agree to the End User License Agreement at https://links.sonatype.com/products/nxrm/ce-eula.'
    eula=requests.post(b+'/service/rest/v1/system/eula',auth=('admin',pw),json={'accepted':True,'disclaimer':disclaimer},timeout=30);assert eula.status_code==204,eula.text
```

**Flow:** GET current state → already accepted ⇒ skip → else refuse LOUD unless env opt-in → on opt-in POST `{accepted:true, disclaimer}` echoing the EULA URL → assert 204. The README (:4) mirrors the same contract for humans: sign in, read, accept in the onboarding wizard; "The template does not accept legal terms on your behalf."
**Invariant:** consent must be an affirmative, informed act — default-deny for automation. `.get('accepted', False)` defaults to NOT-accepted so a schema change fails toward refusal, never toward silent acceptance.
**Probe:** `tests/static.mjs` asserts `/ACCEPT_NEXUS_EULA/` appears in `scripts/smoke.py`. Deterministic probe: `grep -c 'Refusing to accept' scripts/smoke.py` = 1. Runtime caveat recorded (needs a live deployment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "EULA accepted disclaimer", limit: 10 });
```

## Verdict
Adopt the read→check→refuse-unless-opt-in→echo-disclaimer ladder for ANY gated legal/consent surface (works beyond Nexus). Adapt the endpoint and disclaimer text per product/license. Omit nothing behavioral — the fail-toward-refusal default is the portable core.

> ERRATUM pass 5 (deepening-B lane): scripts/smoke.py:11 carries TYPOGRAPHIC quotes around accepted:false / accepted:true (U+2018/U+2019); this excerpt renders them as ASCII apostrophes because repo-hygiene enforces ASCII in this tree — a porter copying legal text must take it from source bytes, not from any capsule.
