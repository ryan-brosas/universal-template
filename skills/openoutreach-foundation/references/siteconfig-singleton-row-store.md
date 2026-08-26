<!-- capsule-v2 -->
# SiteConfig singleton row store — how does a self-hosted single-operator app keep global config without an account model?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Where does global configuration live when there is exactly one operator, and what stops a stray instance from creating a second config row?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/models.py:SiteConfig` (:10-60), esp. `save` (:53-55) and `load` (:58-60).
**Signature:** `def save(self, *args, **kwargs)` (forced `self.pk = 1`); `@classmethod def load(cls) -> "SiteConfig"`.
**Data Shape:** one row at pk=1; blank-string fields mean "unset" (`ai_model`, `llm_api_key`, `llm_api_base`, `bettercontact_api_key`, `contacts_api_token`, `contacts_api_url`, `country_code`). Graph hotspot: save fan-in 32 / load fan-in 28 — every subsystem persists config through this one row.

### Decisive source
```python
def save(self, *args, **kwargs):
    self.pk = 1                      # any instance IS the singleton
    super().save(*args, **kwargs)

@classmethod
def load(cls) -> "SiteConfig":
    obj, _ = cls.objects.get_or_create(pk=1)
    return obj
```

**Flow:** caller mutates fields on the object from `SiteConfig.load()` → `.save()` upserts pk=1 → next reader sees the new value. No cache layer: every read hits the DB.
**Invariant:** Blank means unset — never a sentinel like `"none"`; e.g. blank `bettercontact_api_key` *disables* enrichment, blank `contacts_api_token` means "not registered yet" (resolve misses until the first give-back mints it). Jurisdiction is derived, not stored as a toggle: `country_code` (collected once at onboarding) drives EEA rules via `not is_eea_located`; there is deliberately no stored "contribute to hub" boolean to drift out of sync.
**Probe:** no dedicated suite exists (coverage caveat). Indirect consumers pin behavior: `tests/contacts/test_service.py:152` (`SiteConfig.load().contacts_api_token == "NEW"` after mint), `tests/test_onboarding.py:77` (`country_code == "us"`), `tests/test_discovery_wiring.py:32,:76`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "SiteConfig save load settings store", limit: 10 });
```

## Verdict
Adopt: forced-pk singleton save + `get_or_create(pk=1)` load as the cheapest multi-writer config store; blank-means-unset field semantics; derived jurisdiction over stored toggles. Adapt the field set to your provider keys; omit Django model plumbing. Caveat: singleton semantics are pinned only by indirect tests at this repo — port with your own round-trip test.
