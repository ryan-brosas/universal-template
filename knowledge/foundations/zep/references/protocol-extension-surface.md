<!-- capsule-v2 -->
# Structural protocol extension surface — how do you add a source, transform, submitter, or LLM without base classes?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** What is the package's extension contract, and what hidden obligations come with it?

## Protocols
**Path/Symbol:** `ingestion/src/zep_ingest/protocols.py:26-43` (`Loader`, `Transform`, `Submitter`, `LLMClient`, all `@runtime_checkable Protocol`).
**Signature:** `load() -> Iterator[Episode]`; `apply(episodes: Iterable[Episode]) -> Iterator[Episode]`; `submit(episodes, destination) -> IngestResult`; `complete(prompt: str) -> str`.
**Data Shape:** Transforms are stream-shaped so one protocol covers 1→1 (formatting), 1→many (chunking), and many→1 (grouping) while keeping the whole pipeline lazy.

### Decisive source
```python
# protocols.py module docstring — the obligations the signature hides
# Loaders and transforms may optionally expose a ``warnings: list[str]``
# attribute; Pipeline.run collects it into IngestResult.warnings. A transform
# that accumulates statistics mid-stream may also expose ``flush_warnings()``,
# which Pipeline calls before collecting — a limited preview() can leave the
# episode generator suspended, so warnings must not depend on stream exhaustion.
```

**Flow:** Pipeline treats loader + transforms as a lazy generator chain (`pipeline._stream`: episodes = loader.load(); for t in transforms: episodes = t.apply(episodes)), appends LimitGuard + missing-timestamp counter, then hands the generator to the submitter.
**Invariant:** (1) No inheritance — duck typing only; anything with `apply(Iterable)->Iterator` is a Transform. (2) Optional capabilities are opt-in attributes: `warnings` list is collected per-pass via baseline deltas, `flush_warnings()` exists because a limited `preview(limit=10)` abandons the generator mid-stream — statistics must survive without stream exhaustion. (3) A custom Submitter rejects `method=`/`batch_metadata=` args (ConfigurationError) instead of silently ignoring them.
**Probe:** `grep -c 'flush_warnings' ingestion/src/zep_ingest/protocols.py ingestion/src/zep_ingest/pipeline.py` → 2 (protocol docstring + Pipeline call site); direct test `ingestion/tests/test_protocols.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "Transform Protocol apply Iterator Episode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt runtime_checkable structural protocols + optional-capability attributes (warnings/flush) as the plugin surface; adapt warning plumbing to your result type; omit Zep-specific IngestResult coupling in Submitter if your host has its own.
