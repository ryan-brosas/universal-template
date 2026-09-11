<!-- capsule-v2 -->
# ClaimExtractor covariates — same gleaning grammar as entities, 8-field tuple parser, and a resolved-entities hook that is always empty

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how are claims (covariates) extracted and normalized, and what trap hides in the entity-resolution parameter?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/extract_covariates/claim_extractor.py`: `ClaimExtractor.__call__` (:71-103), `_clean_claim` (:105-117), `_process_document` (:119-163), `_parse_claim_tuples` (:165-193); `extract_covariates.py`: `extract_covariates` (:221-261), `run_extract_claims` (:269-298).
**Signature:** `ClaimExtractor(model, extraction_prompt: str, max_gleanings=None→config default, on_error=None)`; `__call__(texts, entity_spec, resolved_entities, claim_description) -> ClaimExtractorResult{output: list[dict], source_docs: {doc_id: text}}`.
**Data Shape:** claim tuple fields in order — subject_id, object_id, type, status, start_date, end_date, description, source_text; missing fields → None (`pull_field`); document ids are synthetic `d{index}`.

### Decisive source
```python
resolved_entities_map = {}          # ← in extract_covariates.py :235 — NEVER populated
...
claims += RECORD_DELIMITER + extension.strip().removesuffix(COMPLETION_DELIMITER)
...
def _clean_claim(self, claim, document_id, resolved_entities):
    obj = resolved_entities.get(claim.get("object_id", claim.get("object")), ...)  # alias fallback
    obj = resolved_entities.get(obj, obj)      # resolve-or-keep
    claim["object_id"] = obj; claim["subject_id"] = subject
```

**Flow:** per doc (errors → on_error + CONTINUE to next doc) → gleaning loop identical in shape to GraphExtractor's (CONTINUE appends, LOOP probes "Y") → parse the accumulated record string once at the END → clean claims against resolved_entities → caller wraps dicts into Covariate dataclasses and spreads `{**row, **asdict(covariate), "covariate_type"}` into output rows.
**Invariant:** (1) The resolution map is hard-wired EMPTY today — `_clean_claim` is a live seam but a no-op; porters who assume real resolution happens here will double-resolve or crash. (2) Parsing runs AFTER all gleanings accumulate (unlike GraphExtractor which parses the same final string too) — partial failures mid-loop lose everything for that doc via the per-doc try/except. (3) Field access uses `.get()` with alias fallbacks (`object_id` vs `object`) — tolerant of model drift.
**Probe:** no dedicated unit file for ClaimExtractor (verb smoke only); pinned by whole-file reads — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "ClaimExtractor _parse_claim_tuples _clean_claim extract_covariates resolved_entities_map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared gleaning grammar + positional tuple parser for secondary attribute extraction; adapt field names to host schema; treat `resolved_entities_map` as an integration point to IMPLEMENT, not behavior to copy.
