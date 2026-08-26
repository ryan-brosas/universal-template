<!-- capsule-v2 -->
# Episode validation contract — what makes a record submittable, and why validation happens at construction?

**Source:** zep (getzep/zep) Apache-2.0 @ main`7de18dfa14da532cb782a0a14ae329e9a28b23d9`; Codebase Memory `ext-zep`. **Question:** What must be true of every ingested item before any API call, and where is that enforced?

## Episode / Destination / limits
**Path/Symbol:** `ingestion/src/zep_ingest/types.py:25` (`Episode`), `:62` (`Destination`), `:77` (`to_batch_item`), `:90` (`to_graph_add_kwargs`); limits `types.py:13-19`.
**Signature:** `@dataclass(slots=True) class Episode(data: str, data_type: DataType = "text", created_at: str | None = None, metadata: dict | None = None, document: str | None = field(default=None, repr=False))`; `__post_init__` raises `ConfigurationError` aggregating ALL errors.
**Data Shape:** `document` is internal plumbing set by TextChunker to the full source text for LLMContextualizer — it is NEVER sent to the API (to_batch_item/to_graph_add_kwargs simply omit it). `Destination` is frozen and requires EXACTLY ONE of graph_id/user_id (`bool(a)==bool(b)` raises).

### Decisive source
```python
# types.py __post_init__ — collect-all-errors pattern
errors: list[str] = []
if not isinstance(self.data, str) or not self.data.strip():
    errors.append("data must be a non-empty string")
...
if errors:
    raise ConfigurationError("Invalid episode: " + "; ".join(errors))
```

**Flow:** dataclass construction → `__post_init__` validates (non-blank data; data_type ∈ {text,json,message}; RFC3339+TZ timestamp via check_timestamp; metadata via check_scalar_map max_keys=10; document str-or-None) → only then can a submitter map it via `to_batch_item`/`to_graph_add_kwargs`.
**Invariant:** Validation is EAGER at construction ("a bad triple is a clear Python error naming the field — not an HTTP 400 mid-run"). A porter who moves validation into the submit loop loses preview()-before-run correctness: Pipeline.preview() exercises the same constructors with zero API calls. Blank-after-strip data is invalid even though len>0. Timestamps must carry a timezone offset or they are rejected.
**Probe:** `grep -c 'errors.append' ingestion/src/zep_ingest/types.py` → 3 in Episode.__post_init__ (data / data_type+timestamp+metadata via shared checks / document); direct test `ingestion/tests/test_types.py` (29 tests incl. blank-data and bad-data_type cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "Episode Destination post_init validate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt eager collect-all-errors `__post_init__` validation + exactly-one-of destination + never-send-internal-fields mapping helpers; adapt limit constants to your API's documented caps; omit Zep-specific BatchAddItem shape.
