<!-- capsule-v2 -->
# Versioned help RAG cache — how does offline docs search survive upgrades and corrupted caches?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you persist a vector index of bundled docs so each app version gets its own cache and a corrupt one rebuilds instead of breaking `/help`?

## Version-suffixed cache dir; corrupt load → rmtree → rebuild from the packaged corpus
**Path/Symbol:** `aider/help.py`: `get_index` (:84-130), `Help.__init__` (:134-143), `Help.ask` (:145-163), `fname_to_url` (:42-81).
**Signature:** `get_index() -> VectorStoreIndex`; `ask(self, question) -> str`.
**Data Shape:** cache dir = `~/.aider/caches/help.<__version__>` (Path components, not string concat). Each Document carries metadata `{filename, extension, url}`. Retriever: BAAI/bge-small-en-v1.5, `similarity_top_k=20`.

### Decisive source
```python
dname = Path.home() / ".aider" / "caches" / ("help." + __version__)
index = None
try:
    if dname.exists():
        storage_context = StorageContext.from_defaults(persist_dir=dname)
        index = load_index_from_storage(storage_context)
except (OSError, json.JSONDecodeError):
    shutil.rmtree(dname)            # corrupt cache is REMOVED, then rebuilt below
if index is None:
    ...
    for fname in get_package_files():
        if any(fname.match(pat) for pat in exclude_website_pats):
            continue
        doc = Document(text=..., metadata=dict(..., url=fname_to_url(str(fname))))
        nodes += parser.get_nodes_from_documents([doc])
    index = VectorStoreIndex(nodes, show_progress=True)
    index.storage_context.persist(dname)
```

**Flow:** first run of a version builds the index from importlib_resources-packaged markdown (exclusion globs in `help_pats.py`, kept in sync with MANIFEST.in) and persists it. Later runs load it; a failed/corrupt load deletes the directory and falls through to rebuild. `fname_to_url` reconstructs public URLs by splicing at the `website` path segment: `_includes/*` → "", trailing `index.md` stripped, `.md`→`.html`. `ask()` wraps every node as `<doc from_url="...">text</doc>` under a `# Question:` header so the LLM can cite sources.
**Invariant:** a corrupt or partially-written cache must never surface as a user-facing failure — deletion plus rebuild is the recovery path, and per-version keys prevent stale-schema loads after upgrades.
**Probe:** direct tests: `tests/help/test_help.py::test_fname_to_url_unix/windows/edge_cases` (:98-143) pin the URL reconstruction table (`website/docs/index.md`→`https://aider.chat/docs`, `_includes/header.md`→"", non-website paths →""). Executed this pass: `.venv/bin/python -m pytest tests/basic/test_models.py -k 'extra...' tests/help/test_help.py::TestHelp::test_fname_to_url_{unix,windows,edge_cases} -q` → **6 passed**. Caveat: `test_init`/`test_ask_without_mock` download the embedding model — deterministic anchors only for those claims.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_index", limit: 10 });
// rank-1: aider.aider.help.get_index Function aider/help.py 84-130 (Help.ask :145-163 rank-2)
```

## Verdict
Adopt version-suffixed cache directories with delete-and-rebuild recovery for any embedded RAG index. Adapt the embedder/top-k to your stack and the URL splicer to your docs layout. Omit llama_index specifics if your host has its own vector store — the contract is "version-keyed dir + corrupt-rmtree + packaged-corpus rebuild", not the library.
