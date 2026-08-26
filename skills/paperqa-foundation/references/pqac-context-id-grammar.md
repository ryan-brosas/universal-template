<!-- capsule-v2 -->
# pqac context-ID grammar — how does a citation key stay stable, short, and collision-safe across retries?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How is the in-text citation key (`pqac-xxxxxxxx`) computed so the answer LLM can cite it, the bibliography can resolve it, and identical contexts dedupe?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/types.py:Context` (:238-316; `REFERENCE_TEMPLATE = "pqac-{id}"`, `ID_HASH_LENGTH = 8`, `CONTEXT_ENCODING_LENGTH = 500`) + `utils.encode_id` (:244-250).
**Signature:** `id: str = Field(default=AUTOPOPULATE_VALUE)` populated by `model_validator(mode="before") populate_id`.
**Data Shape:** `content = question + context[:500]`; `id = "pqac-" + md5(content)[:8]`. Empty content falls back to `uuid4()` (still deterministic-shaped). Context equality/hash includes extras; `PQASession.used_contexts` is `{c.id for c in contexts if c.id in raw_answer}` — substring membership of the id in the raw answer.

### Decisive source
```python
CONTEXT_ENCODING_LENGTH: ClassVar[int] = 500  # chars
ID_HASH_LENGTH: ClassVar[int] = 8  # chars
REFERENCE_TEMPLATE: ClassVar[str] = "pqac-{id}"

@model_validator(mode="before")
@classmethod
def populate_id(cls, data):
    if not data.get("id"):  # NOTE: includes missing or empty strings
        content = (data.get("question") or "") + data.get("context", "")[: cls.CONTEXT_ENCODING_LENGTH]
        return data | {"id": cls.REFERENCE_TEMPLATE.format(
            id=encode_id(content or str(uuid4()), maxsize=cls.ID_HASH_LENGTH))}
    return data
```

**Flow:** Same (question, first-500-chars) ⇒ same id ⇒ duplicate contexts collapse in `docs.aget_evidence`'s set-comprehension (:579-585). The prompt shows `(pqac-0f650d59)` as the example citation and FORBIDS concatenation/semicolons (`prompts.CITATION_KEY_CONSTRAINTS` :38-50); the bibliography parser only trusts comma/space-delimited ids inside parentheticals.
**Invariant:** The hash input is truncated at exactly 500 CHARS (not tokens) BEFORE hashing — hashing after truncation elsewhere changes ids and breaks dedupe; `UNSET_RELEVANCE = -1` sorts below any real score.
**Probe:** `tests/test_paperqa.py::test_pqa_context_id_parsing` (:3475) + executed lifted probe T4/T5a-T5b (md5(question+ctx[:500])[:8]; order-preserving dedup via `get_citation_ids`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "pqac REFERENCE_TEMPLATE populate_id encode_id", limit: 10 });
```

## Verdict
Adopt the id grammar verbatim (prefix+8-hex keeps regexes simple and human-checkable); adapt length constants if your corpus needs fewer collisions; omit uuid fallback only if you accept crashes on empty contexts. Coverage: cited paths no_recorded_issue; probes GREEN.
