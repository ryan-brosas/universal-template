<!-- capsule-v2 -->
# IndexSchema field-name guard — why does a "vector index config" validate identifiers like a database would?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what exactly does the schema validator enforce at construction time and which fields escape validation?

## model_validator gate
**Path/Symbol:** `packages/graphrag-vectors/graphrag_vectors/index_schema.py` (`DEFAULT_VECTOR_SIZE` :10, `VALID_IDENTIFIER_REGEX` :12, `is_valid_field_name` :15-17, `IndexSchema` :20-61).
**Signature:** `is_valid_field_name(field: str) -> bool` = `^[A-Za-z_][A-Za-z0-9_]*$` full-match; `_validate_schema` runs in `@model_validator(mode="after")`.
**Data Shape:** `IndexSchema{index_name="vector_index", id_field="id", vector_field="vector", vector_size=3072, fields: dict[str,str] (str|int|float|bool|date)}`.

### Decisive source
```python
# index_schema.py:47-55 — ONLY id_field and vector_field are checked;
# the `fields` map values (and index_name itself) pass through unvalidated —
# a porter who assumes "the schema validates everything" will ship
# injection-prone metadata fields to CosmosDB backends
def _validate_schema(self) -> None:
    for field in [self.id_field, self.vector_field]:
        if not is_valid_field_name(field):
            msg = f"Unsafe or invalid field name: {field}"
            raise ValueError(msg)
```

**Flow:** GraphRagConfig auto-injects one IndexSchema per known embedding into `vector_store.index_schema` during config validation → factory merges schema dict into store kwargs (`{**config_model, **index_model}`) → invalid id/vector field names FAIL AT CONFIG LOAD, not at first query.
**Invariant:** the docstring says the regex exists FOR COSMOSDB ("valid for CosmosDB" :16) — it is a lowest-common-denominator identifier rule applied globally; timestamp-explosion-generated names are safe by construction (`{prefix}_{suffix}` with validated prefix); vector_size 3072 matches common embedding dims but is NOT cross-checked against actual embedder output — mismatch surfaces as backend insert errors, not config errors.
**Probe:** no dedicated unit file for index_schema; behavior pinned via source greps @pin (`grep -c 'VALID_IDENTIFIER_REGEX' index_schema.py` = 2, `grep -c 'Unsafe or invalid field name' index_schema.py` = 1) and by the config-model capsule's graph_rag_config auto-injection citation. Recorded caveat: verified by direct read, not executed test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "IndexSchema vector size valid field name validator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt construction-time identifier validation for the two load-bearing fields + fail-fast ValueError; adapt regex to strictest target backend; if your host accepts user-supplied metadata FIELD names, extend validation to them (upstream deliberately scopes down).
