<!-- capsule-v2 -->
# Hunter last-resort — when does the paid email-finder run, what does it cost, and why is its output scored like a guess?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** Under exactly which conditions does `_find_with_hunter` fire, and what contract does its returned address enter the candidate funnel with?

## Gated paid lookup whose result competes at base score 80, never verified
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._find_with_hunter` (:507-533); dispatch gate in `enrich_lead` (:88-93); scoring treatment in `_score_and_verify_email` (`source == 'hunter.io'` → +80, :351-352) and lead-score bonus (+5, :540-541).
**Signature:** `_find_with_hunter(full_name: Optional[str], website: Optional[str]) -> Optional[str]`.
**Data Shape:** requires ALL of `self.hunter_api_key`, non-empty `full_name` with ≥2 whitespace-split parts, and a domain-extractable `website`; returns the bare email string from `data['data']['email']` or None. Graph carries the wire contract as nodes: Route `GET https://api.hunter.io/v2/email-finder` and EnvVar `HUNTER_API_KEY`.

### Decisive source
```python
# dispatch — three-part gate, checked BEFORE any HTTP spend:
if self.hunter_api_key and lead_data.get('full_name') and website:
    hunter_email = self._find_with_hunter(
        lead_data.get('full_name'), website
    )
    if hunter_email:
        email_candidates.append((hunter_email, 'hunter.io'))   # LAST position

# inside _find_with_hunter:
parts = full_name.split()
if len(parts) < 2:
    return None                       # single-name leads never hit the API
resp = httpx.get('https://api.hunter.io/v2/email-finder', params={
    'domain': domain,
    'first_name': parts[0],
    'last_name': parts[-1],           # FIRST part + LAST part; middles dropped
    'api_key': self.hunter_api_key,
}, timeout=10)
data = resp.json()
if data.get('data', {}).get('email'): # .get-chain ⇒ malformed body → None
    return data['data']['email']
```

**Flow:** runs after pattern prediction AND (when reached) the smtp_guess block, but note it is **not** behind the empty-funnel guard — Hunter fires even when free sources already found candidates, appending its (usually duplicate) address at the end where case-insensitive first-wins dedup makes it a no-op unless the earlier claim came from a lower tier... which it can't, because 80 is second only to bio's 90. Its one real job: supply an address when nothing else did, or outscore a weak `'pattern'`(40)/`'bio_link'`(65) find. The returned email is scored (+80) and SMTP-verified like every other candidate; if SMTP says accept-all it still loses 20.
**Invariant:** the API key check happens TWICE by design — once at dispatch (skip without spend) and once inside (`if not self.hunter_api_key ... return None`), so direct callers can't bypass the guard either. Position in the candidate list IS priority: append order encodes "paid lookup is last resort." Name handling takes `parts[0]`/`parts[-1]` — middle names silently vanish into the query, not an error. Any exception (network, JSON, missing key) degrades to None via the broad except; Hunter failure never blocks other sources.
**Probe:** no direct test (zero-test repo). Deterministic probes: `grep -c 'hunter_api_key' app/scrapers/enrichment.py` → **7** occurrences incl. both gates; `grep -cF 'api.hunter.io/v2/email-finder' app/scrapers/enrichment.py` → **1**; graph retrieval resolves the Route node for the endpoint plus EnvVar `HUNTER_API_KEY`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "hunter email finder api", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the double-gate + ordered-candidate position + verify-after-purchase discipline (never trust a paid lookup more than your own SMTP probe); adapt the provider/tier scores if you swap vendors; omit the branch entirely when you hold no key — Scout itself ships that way (`hunter_api_key=None` default) and the funnel stays complete.
