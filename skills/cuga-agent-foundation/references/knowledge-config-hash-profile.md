<!-- capsule-v2 -->
# Knowledge config audit-hash & profile layering — how does a porter hash adaptation/glossary for observability without leaking text, and layer profile addenda without touching the canonical contract?

**Source:** cuga-agent (Apache-2.0) `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The knowledge prompt carries operator-authored client-adaptation rules and a glossary, and per-profile instruction addenda. A porter needs (a) a stable, non-leaky audit fingerprint of these so SREs correlate complaints to config versions without logging PII/prompt-IP, and (b) a way for named RAG profiles to layer extra instructions into the prompt without the profile mutating the canonical contract.

## Config-layer hashing + profile loader
**Path/Symbol:** `src/cuga/backend/knowledge/config.py` — `client_adaptation_hash(text)` (377-385), `client_glossary_hash(entries)` (388-400), `load_profile(profile_name)` (411-450, pass-18 refresh: #679 now rejects unknown names with ValueError BEFORE path building and joins via `child_path_under` so a published name cannot traverse — see knowledge-metadata-normalization capsule), `list_profiles()` (452+). Consumer: `src/cuga/backend/knowledge/awareness.py` `get_knowledge_summary` — hash log (313-329), profile addendum injection (331-344).
**Signature:** `def client_adaptation_hash(text: str) -> str`; `def client_glossary_hash(entries: list[dict[str, Any]] | None) -> str`; `def load_profile(profile_name: str) -> dict[str, Any]`.
**Data Shape:** Both hashes are the first 12 hex chars of SHA256 (stable, scoped, non-leaky). `client_adaptation_hash` hashes the normalized text; empty string → one well-known value meaning "no adaptation set". `client_glossary_hash` JSON-serializes with `sort_keys=True` (order-stable per dict) but preserves entry order (aliases are semantically ordered). `load_profile` reads `<profile_name>.toml` from `_PROFILES_DIR` via `tomllib`, raising `FileNotFoundError` when missing; returns `{profile, search, chunking, instructions}`. `list_profiles` iterates `VALID_PROFILES`, skipping failures with a warning.

### Decisive source
```python
def client_adaptation_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]

def client_glossary_hash(entries):
    entries = entries or []
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

# awareness.py get_knowledge_summary — never log the text itself (PII / prompt-IP)
if has_adapt:
    logger.info("cuga.knowledge.adaptation_applied", extra={
        "cuga_knowledge_adaptation_hash": client_adaptation_hash(adapt_body),
        "cuga_knowledge_adaptation_len": len(adapt_body),
        "cuga_knowledge_glossary_hash": client_glossary_hash(glossary),
        "cuga_knowledge_glossary_entries": len(glossary), ...})

# Profile addendum — owned by the profile, not the canonical contract
if rag_profile and rag_profile != "standard":
    try:
        profile_data = load_profile(rag_profile)
        addendum = profile_data.get("instructions", {}).get("addendum", "").strip()
        if addendum:
            summary += f"\n{addendum}\n"
    except Exception as e:
        logger.warning(f"Failed to load profile addendum for {rag_profile}: {e}")
```

**Flow:** `get_knowledge_summary` renders the adaptation block → if `has_adapt` (non-empty body OR glossary), logs ONLY hash + length + entry count + collection names (never the text) → if a non-standard `rag_profile` is set, loads its TOML, extracts `instructions.addendum`, and appends it to the summary; any failure (missing file, bad TOML, missing key) is a warning, never fatal → the recency tail ("BEFORE you respond…") is appended only when `has_adapt`.
**Invariant:** The hash is computed AFTER normalization so NFC-different copy-paste inputs produce the same hash (no "mystery diffs"); empty-string adaptation hashes to one well-known value so "no adaptation set" is trivially diffable; the glossary hash is structure-aware (sorted keys) yet preserves alias order; the addendum is layered ON TOP of the composed summary and is profile-owned — a profile can add "be terse" or "always cite sources" without the canonical `knowledge_instructions.md` contract changing; a missing/non-loadable profile degrades to a warning (never blocks prompt assembly), and `rag_profile == "standard"` skips the addendum branch entirely.
**Probe:** `tests/unit/test_knowledge_client_adaptation.py` — `TestClientAdaptationHash` (475-502): `test_stable_across_calls`, `test_empty_string_hash_is_well_known`, `test_different_inputs_different_hashes`, `test_hash_is_12_chars`, `test_hash_surfaces_in_get_settings` (inspects `KnowledgeEngine.get_settings` source to pin the hash field path). `tests/unit/test_knowledge_config_perf_keys.py` pins `load_profile` behavior: a non-existent profile (`rag_profile="__no_such_profile____"`) is treated as "no profile data" without raising, so `settings.toml` becomes the source of truth. Coverage caveat: the prompt-injection addendum branch (`rag_profile != "standard"` in `get_knowledge_summary`) has no dedicated unit test — it is exercised only indirectly via profile-loading tests; the hash helpers and their get_settings surface are directly pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "client_adaptation_hash client_glossary_hash load_profile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 12-hex-SHA256 audit hashing (adaptation text, structure-aware glossary) with the never-log-the-text contract and the well-known-empty value; adopt the profile-addendum layering (non-standard profile TOML `instructions.addendum` appended to the summary, warning-not-fatal on failure, `standard` skips); adapt the hash prefix length, the profile TOML schema, and the `_PROFILES_DIR`/`VALID_PROFILES` locations to your host; omit the specific `knowledge_profiles/*.toml` contents. Direct tests pin the hash helpers + get_settings surface and the non-existent-profile fallback; the addendum prompt-injection branch itself is source-confirmed but not directly unit-tested.
