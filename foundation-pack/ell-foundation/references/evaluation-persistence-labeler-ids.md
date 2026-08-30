<!-- capsule-v2 -->
# evaluation persistence and labeler ids — how do evaluation versions, runs, and labels get deterministic identity?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How are evaluations content-addressed so re-running an unchanged eval doesn't fork new rows, while every label still traces to its labeling invocation?

## hash-composed evaluation id + composite labeler id
**Path/Symbol:** `src/ell/evaluation/serialization.py:write_evaluation` (:33-92), `write_evaluation_run_start` (:94-104), `write_evaluation_run_intermediate` (:106-125); id minters `src/ell/stores/models/evaluations.py:EvaluationLabeler.generate_id/validate_id` (:47-61); helpers `ido`/`hsh` (`src/ell/util/closure_util.py` :165-172).
**Signature:** `EvaluationLabeler.generate_id(evaluation_id, name, type) -> "labeler-{evaluation_id}-{name}-{TYPE}"` (lru_cache 128); `hsh(x) -> md5hex` (lru_cache 128); `ido(f) -> f.__ell_func__.__ell_hash__`.
**Data Shape:** `evaluation.id = "evaluation-" + hsh(dataset_id + "".join(sorted(metric_ids) + sorted(annotation_ids) + criterion_ids))`; dataset blob id `"dataset-" + hsh(serialized_dataset)`.

### Decisive source
```python
# serialization.py:37-52
if not evaluation.has_serialized:
    serialized_dataset = serialize_object(evaluation.dataset)
    dataset_id = "dataset-" + hsh(serialized_dataset)
    if config.store.has_blob_storage:
        config.store.blob_store.store_blob(serialized_dataset.encode("utf-8"), dataset_id)
    metrics_ids = [ido((f)) for f in evaluation.metrics.values()]
    annotation_ids = [ido((a)) for a in evaluation.annotations.values()]
    criteiron_ids = [ido((evaluation.criterion))] if evaluation.criterion else []

    evaluation.id = "evaluation-" + hsh(dataset_id + "".join(sorted(metrics_ids) + sorted(annotation_ids) + criteiron_ids))

    existing_versions = config.store.get_eval_versions_by_name(evaluation.name)
    if any(v.id == evaluation.id for v in existing_versions):
        evaluation.has_serialized = True
```

```python
# evaluations.py:50-56 — the id IS a parseable contract
@field_validator("id")
def validate_id(cls, v):
    if v is not None:
        assert v.startswith("labeler-")
        evaluation, eid, name, type = v.split("-")[1:]
        assert evaluation == "evaluation"
        assert type in EvaluationLabelerType.__members__
        return v
```

**Flow:** dataset serialized → hashed → optionally stored as a blob; each labeler contributes its LMP HASH (content identity of the metric code itself, via `ido`); the joined sorted-id string hashes into the evaluation id; same id under the same name marks the evaluation as already serialized (no new version). Run start writes a row keyed by the evaluated LMP's hash; intermediate writes create datapoint + one EvaluationLabel per output label, each carrying `label_invocation_id` — the invocation that PRODUCED the label, closing the audit loop from score back to model call.
**Invariant:** labeler identity is code-content-based (edit a metric → new evaluation id), while name groups versions; and labeler ids must survive round-trip through the validator's dash-splitting — names containing dashes would corrupt the parse (latent upstream hazard worth fixing in any port).
**Probe:** `tests/test_evaluation.py:test_evaluation_initialization` (:30-) pins label assembly; store-side versioning pinned by `tests/test_migrations.py:test_existing_tables_no_alembic` (:101-119) which asserts the head revision carrying these tables.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "evaluation labeler generate id", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.stores.models.evaluations.EvaluationLabeler.generate_id @ src/ell/stores/models/evaluations.py:60-61
```

## Verdict
Adopt content-hash composition for eval identity and invocation-linked labels. Adapt the delimiter scheme (use something name-safe). Omit blob-stored datasets only if your datasets are tiny — but keep hashing over the SERIALIZED form, not the Python object, or identity stops being stable across processes.
