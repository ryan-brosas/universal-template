<!-- capsule-v2 -->
# Media enrichment & irrelevance filter — when do parsed images/tables earn descriptions, and who decides they are junk?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How are PDF images/tables enriched with LLM captions BEFORE chunking, how is the RELEVANT/IRRELEVANT label protocol parsed fail-safe, and what happens to oversized or corrupt media?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/settings.py:Settings.make_media_enricher/enrich_media_with_llm` (:1051-1193) + `utils.parse_enrichment_irrelevance` (:671-688) + `prompts.individual_media_enrichment_prompt_template` (:171-213) + `MultimodalOptions` (:207-230).
**Signature:** `def make_media_enricher(self) -> Callable[[ParsedText], Awaitable[str]]`; enricher returns summary `"enriched={n}|filtered={n}|radius={r}"` which is EMBEDDED into ChunkMetadata.name.
**Data Shape:** `ParsedMedia(index, data|url xor-validated, text?, info{enriched_description, is_irrelevant, page_num, suffix})`; deterministic UUID via seeded sha256(data+text)→Random.getrandbits(128) with version/variant bits forced (:625-651). Enrichment runs on WHOLE parsed text pre-chunk so captions see ±radius pages.

### Decisive source
```python
normalized_start = enrichment.upper().lstrip("*").lstrip()
if normalized_start.startswith("IRRELEVANT:"): ...
elif normalized_start.startswith("RELEVANT:"): ...
else: return False, enrichment.strip()   # NO label ⇒ conservatively RELEVANT
...
except (litellm.InternalServerError, litellm.BadRequestError) as exc:
    if (isinstance(exc, litellm.InternalServerError)
            and re.search(r"image exceeds .+ maximum", str(exc), re.IGNORECASE)) \
       or isinstance(exc, litellm.BadRequestError):
        logger.warning("Skipping enrichment ... rejected by the LLM provider")  # degrade, keep media
    else:
        raise
```
Radius semantics: -1 all pages / 0 current / N surrounding; default 1 because "figures are usually +/- 1 page in LaTeX".

**Flow:** gather un-enriched media across pages (dedup deliberately NOT done — documented tradeoff comment :1071-1076) → parallel caption calls with page-radius co-located text → label parse (markdown-tolerant, unlabeled=relevant) → in-place filter of `is_irrelevant` media per page → counts returned. MultimodalOptions tri-state OFF/ON_WITH_ENRICHMENT/ON_WITHOUT_ENRICHMENT maps to (parse?, enrich?).
**Invariant:** Unlabeled enrichment output keeps media (fail-open to keeping evidence); provider rejection skips ONLY the caption, never drops the image; `data XOR url` enforced at validation ("both creates ambiguous state... convert instead").
**Probe:** `tests/test_paperqa.py::test_duplicate_media_context_creation` (:2425); clients of enrichment in `core._map_fxn_summary` multimodal branch (:234-267) with opt-in text-only fallback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "make_media_enricher parse_enrichment_irrelevance ParsedMedia", limit: 10 });
```

## Verdict
Adopt pre-chunk enrichment + labeled-protocol fail-open + skip-not-drop degradation; adapt caption model default (gpt-4o chosen from CapArena benchmarking, noted in-source); omit full-page screenshot variant if you never render pages as images.
