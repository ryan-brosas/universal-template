<!-- capsule-v2 -->
# Neptune datetime parameter splicing — how do you pass datetimes through a driver whose Cypher dialect has no datetime parameter binding?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`neptune_driver.py:_sanitize_parameters/_run_query`); Codebase Memory `graphiti`. **Question:** When parameters arrive as Python `datetime` objects but the backend can't bind them natively, where exactly do they become strings — and which query text gets rewritten behind the caller's back?

## Recursive value coercion + `$param` → `datetime($param)` text rewrite
**Path/Symbol:** `graphiti_core/driver/neptune_driver.py:NeptuneDriver._sanitize_parameters` (:243–278), `_run_query` (:292–302), `execute_query` (:280–290).
**Signature:** `_sanitize_parameters(self, query, params: dict)` — mutates `params` IN PLACE and returns rewritten query text.
**Data Shape:** accepts str OR list-of-(q,params)-pairs queries (batch form executed serially, last result wins); params may nest lists/dicts of datetimes.

### Decisive source
```python
for k, v in params.items():
    if isinstance(v, datetime.datetime):
        params[k] = v.isoformat()
    elif isinstance(v, list):
        for i, item in enumerate(v):
            if isinstance(item, datetime.datetime):
                v[i] = item.isoformat()
                query = str(query).replace(f'${k}', f'datetime(${k})')
        # If the list contains datetime objects, wrap each element:
        if any(isinstance(item, str) and 'T' in item for item in v):
            datetime_list = ('[' + ', '.join(
                f'datetime("{item}")' if isinstance(item, str) and 'T' in item else repr(item)
                for item in v) + ']')
            query = str(query).replace(f'${k}', datetime_list)
```

**Flow:** `execute_query` copies kwargs into a plain dict; batch queries loop pairwise. `_run_query` ALWAYS runs sanitize first (even when nothing needs changing), coerces the query to `str`, then calls `self.client.query(...)`; failures log query+params at ERROR level then RE-RAISE (log-and-raise, callers still own the error). Sanitization rules: top-level datetime → ISO string in place (no query rewrite needed — Neptune binds ISO strings where openCypher expects temporal literals? No: scalar case relies on the server accepting ISO strings); datetime INSIDE a list → ISO-coerce the element AND rewrite every `${k}` occurrence in the query text to `datetime(${k})`; a heuristic second pass treats any string containing `'T'` inside a mixed list as a datetime literal and SPLICES THE VALUES DIRECTLY INTO THE QUERY TEXT as `datetime("...")` inline literals (repr() for non-datetime items). Nested dicts recurse.
**Invariant:** the mutation is invisible to callers — `params` is mutated in place AND query text is rewritten, so the same params dict passed twice gets double-processed (idempotence is NOT guaranteed for the `'T'-in-string` splice path; a pre-spliced literal would be wrapped again). The `'T'` substring heuristic can false-positive on ordinary strings containing T. Porters must make sanitization idempotent or single-shot.
**Probe:** coverage caveat — no direct tests (`tests/driver/` holds FalkorDB suites only). Deterministic probe: sanitize a params dict twice with a `'2026-01-01T00:00:00'` list element and observe double-wrapping on the second pass; assert log-and-re-raise on injected client exception.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "_sanitize_parameters datetime execute_query NeptuneDriver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: explicit coerce-at-the-boundary for temporal params with a documented rewrite point. Adapt the `datetime()` wrapper syntax to your dialect (FalkorDB solves the same problem differently — see `falkordb-driver.md` ISO coercion; comparing both is the fastest way to understand the constraint space). Omit the `'T'`-heuristic splice unless you enjoy injection-shaped surprises; prefer typed coercion ladders over substring detection.
