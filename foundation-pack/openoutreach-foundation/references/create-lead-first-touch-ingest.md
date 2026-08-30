<!-- capsule-v2 -->
# create_lead first-touch ingest — how does a deduped discovery row split "who found it" from "what the model learns"?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** When the same person is surfaced by many query nodes, what gets stamped on first touch, and where do query keywords belong in the training data?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/db/leads.py:create_lead` (:35-80); twin exclusions `disqualify_lead` (:83-92).
**Signature:** `create_lead(row: dict, country_code: str = "", discovered_by=None, query_terms: str = "") -> bool`.
**Data Shape:** keyed on `row["contact_linkedin_profile_url"]` (missing ⇒ return False); `get_or_create` defaults carry embedding bytes, profile_text, source_fields, company FK, person columns; returns `created`.

### Decisive source
```python
_, created = Lead.objects.get_or_create(
    profile_url=profile_url,
    defaults={
        "embedding": np.asarray(
            embed_profile(profile_text, query_terms), dtype=np.float32).tobytes(),
        ...
    },
)
return created   # False on idempotent re-discovery
```
Its docstring states the split this capsule protects:
> ``discovered_by`` ... lands only on first touch ... Its ``query_terms`` are folded into the **embedding only** — not ``profile_text`` — so the GP learns which query keywords surface good leads while the LLM judges the person on firmographics alone.

**Flow:** discovery page row → get_or_create by opaque provider URL → new rows get embedding+text stamped once (qualification never re-fetches) → duplicate pages are no-ops that still let the walk advance.
**Invariant:** Three separations in one write. (1) Provenance is first-touch only — re-discovery keeps the original node (`discovered_by` records who *found* it, not everyone who saw it; SET_NULL keeps the Lead if its node is pruned). (2) Query terms enter the vector but never the LLM's text — otherwise the qualifier would read search-engine noise as person facts. (3) Rejection has two scopes: campaign-scoped FAILED deals vs `disqualify_lead`'s permanent account-level flag written with `update_fields=["disqualified"]`. The removed `suppress_email` inbound path is documented as a legal position (a finder that never contacts anyone inherits no CAN-SPAM/GDPR sender duty).
**Probe:** `tests/test_discovery_wiring.py::TestHarvest` (:88-114 — created==1 pins `Lead.objects.get().discovered_by_id == node.pk` at :102; duplicate page still advances at :104-114) + `tests/test_discovery.py::TestEmbedProfile` (:161-173, the embedding-split twin).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "create_lead get_or_create discovered_by query_terms embedding", limit: 10 });
```

## Verdict
Adopt: get_or_create ingest returning a created bool so callers can distinguish new evidence from duplicates; provenance stamped once at first touch; channel/search metadata kept out of the text an LLM judges. Adapt identity key to your provider's stable URL; omit Django/numpy specifics.
