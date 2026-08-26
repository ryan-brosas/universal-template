<!-- capsule-v2 -->
# Knowledge config validation ladder — how do you validate a runtime-editable config so a prompt-injection vector can't slip through the UI, and which fields must NOT invalidate vectors?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A manage UI lets operators PATCH the knowledge config live — what safety validation runs on `client_adaptation_text`/glossary, how does `coerce_and_validate` layer profile defaults under explicit overrides, and what distinguishes vector-affecting fields from search-only fields?

## Validation ladder + coercion + hash partitioning
**Path/Symbol:** `src/cuga/backend/knowledge/config.py:147-201` (`_validate_client_adaptation`), `:203-329` (`_validate_glossary`), `:332-374` (`_scan_unsafe_chars`), `:377-400` (`client_adaptation_hash`/`client_glossary_hash`), `:656-672` (`vector_config_hash`), `:674-830` (`validate`), `:843-995` (`coerce_and_validate`), `:997-1131` (`from_settings`).
**Signature: `_validate_client_adaptation(text) -> None` raising `ClientAdaptationError(code, message, **detail)`; `_validate_glossary(entries) -> list[dict]`; `coerce_and_validate(incoming: dict, base=None) -> KnowledgeConfig`; `vector_config_hash() -> str` (12-hex sha256).**
**Data Shape:** `ClientAdaptationError.to_dict()` = `{"error": code, "message": ..., **detail}`. Glossary entry canonical shape `{"term": str, "aliases": [str], "definition": str}`.

### Decisive source
```python
# config.py:158-200 — ordered rejection ladder: length → null byte → bidi → control → denylist
if len(text) > CLIENT_ADAPTATION_MAX_CHARS:  # 3000
    raise ClientAdaptationError("length_exceeded", ...)
if "\x00" in text:
    raise ClientAdaptationError("null_byte", ...)
for cp in text:
    if cp in _BIDI_OVERRIDE_CODEPOINTS:  # U+202A..E, U+2066..9
    raise ClientAdaptationError("bidi_override", ...)
    if cp in _PERMITTED_CONTROL_CHARS: continue  # \t \n \r
    if (0x00 <= ord(cp) <= 0x1F) or (0x80 <= ord(cp) <= 0x9F):
        raise ClientAdaptationError("control_char", ...)
for pattern in _CLIENT_ADAPTATION_DENYLIST:  # ignore/disregard/forget/you-are-now/override regexes
    m = pattern.search(text)
    if m:
        raise ClientAdaptationError("contract_override_phrase", ...)
```

**Flow:** `validate()` runs the freeform text through `_validate_client_adaptation` and normalizes the glossary via `_validate_glossary` in place (callers see the cleaned form). `_validate_glossary` skips empty/blank terms silently (the UI synthesizes an empty-term row on "Add term" click — rejecting would 422 every click), NFC-normalizes each field, case-fold dedupes terms and aliases, and runs `_scan_unsafe_chars` (bidi + control + the SAME denylist) on EVERY text field — term, aliases, definition — so a jailbreak phrase can't bypass the adaptation-text denylist by hiding in a glossary cell. `coerce_and_validate` first applies the named `rag_profile` TOML values as the merged base (profile "owns" embedding_model/chunking/rerank/docling/search/engine defaults), then layers explicit `incoming` keys on top (they supersede the profile), coercing bool/int/float/str per target type, treating `embedding_provider="auto"` as `fastembed`, and ignoring unknown keys. `vector_config_hash` includes ONLY `storage.mode | embedding_provider | embedding_model | chunk_size | chunk_overlap | metric_type` — deliberately EXCLUDES `citations_enabled`, `client_adaptation_text`, `client_adaptation_glossary`, `rag_profile`, `rerank_enabled`, `search_query_transform` (prompt/search-only changes never invalidate vectors). `validate()` also enforces: `metric_type == "COSINE"` ONLY (IP/L2 would silently use a cosine index — reject loudly), `rerank_top_k_in >= 3 * default_limit` when rerank enabled (recall-ceiling contract), OpenRouter/LiteLLM require explicit `embedding_model`, and `embedding_extra_params` values must be str/int/float/bool (snapshot-safe).

**Invariant:** The adaptation text + glossary are appended to the knowledge-agent system prompt, so they're validated as hostile input with a machine-readable error `code` per failure mode (UI renders specific affordances). The denylist is explicitly NOT a security boundary (defense-in-depth only) — it catches obvious self-service jailbreaks but a determined attacker has other vectors. `vector_config_hash` is the single source of truth for "does this config change force re-ingest" — prompt edits must never flip it.

**Probe:** `tests/unit/test_knowledge_client_adaptation.py:393` (`test_contract_override_phrase_rejected`, parametrized denylist), `:432` (`test_bidi_override_rejected`), `:440` (`test_disallowed_control_chars_rejected`), `:446` (`test_tab_lf_cr_permitted`), `:451` (`test_nfc_normalization_on_coerce`), `:594-712` (glossary validation: blank-term skip, dup rejection, alias dedup, denylist-on-every-field at `:923`), `:721-728` (hash stability), `:77` (`test_vector_hash_unaffected_by_adaptation`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_validate_client_adaptation _validate_glossary coerce_and_validate vector_config_hash ClientAdaptationError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered validation ladder (length→null→bidi→control→denylist) with machine-readable error codes, the glossary safety scanner reused on every field, the profile-under-explicit-override coercion, and the strict hash partitioning (vector-affecting vs search-only). Adapt the denylist regex set and char caps to your deployment. Omit the `from_settings` dynaconf plumbing unless you use dynaconf. Direct-test coverage is strong for validation/hash; the denylist phrase set itself is the only heuristic surface.
