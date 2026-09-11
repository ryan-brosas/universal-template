<!-- capsule-v2 -->
# Repo-parsing chunk plane — how do you build the whole-repo snippet corpus that the search planes consume (filtering, chunking, caching, parallelism)?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** Before lexical/vector search can score anything, someone must turn a cloned repo into a chunk corpus — what decides which files are human-readable code, how are they chunked and cached, and what is the single production consumer?

## directory_to_chunks: memoized readability filter → scandir DFS with pruning → path+content-hash chunk cache → Pool-imap tree-sitter chunking
**Path/Symbol:** `sweepai/core/repo_parsing_utils.py` whole (168L): `chunk_cache`/`file_name_cache` (:18–19), `filter_file` (:23–29), `_filter_file` (:31–80), `read_file` (:83–88), `FILE_THRESHOLD` (:90), `conditional_hash` (:92–95), `file_path_to_chunks` (:97–105), `directory_to_chunks` (:108–147); chunker `sweepai/utils/code_validators.py:chunk_code` (:603–643, default MAX_CHARS = AVG_CHAR_IN_LINE*200 = 12000 at :606, coalesce=80). **Single production caller:** `sweepai/core/lexical_search.py:prepare_lexical_search_index` (:216–250, @streamable; call at :234).
**Signature:** `directory_to_chunks(directory, sweep_config, do_not_use_file_cache=False) -> tuple[list[Snippet], list[str]]`; `filter_file(directory, file, sweep_config) -> bool` (True = include); `file_path_to_chunks(file_path) -> list[Snippet]`.
**Data Shape:** input = repo root on disk + SweepConfig exclusion tables; output = flat list of Snippet chunks (content = full file text with start/end delimiting the range) + the surviving file list.

### Decisive source
```python
chunk_cache = Cache(f'{CACHE_DIRECTORY}/chunk_cache')   # :18 — diskcache singletons, diskcache handles concurrency
file_name_cache = Cache(f'{CACHE_DIRECTORY}/file_name_cache')
...
def _filter_file(directory, file, sweep_config):        # :31 — the readability ladder
    for ext in sweep_config.exclude_exts: ...
    for dir_name in sweep_config.exclude_dirs:
        for file_part in only_file_name_parts[:-1]:     # parent dirs ONLY (filename part exempt)
            if file_part == dir_name: return False
    for dir_name in sweep_config.exclude_path_dirs:
        if dir_name in only_file_name_parts: return False
    size = os.stat(file).st_size
    if size > 240000 or size < 10: return False         # :56
    data = read_file_with_fallback_encodings(file)      # UnicodeDecodeError ⇒ out
    if b'\x00' in data.encode(): return False          # binary
    if len(data) / line_count > 200: return False       # avg line length ⇒ not human readable
    token_count = tiktoken_client.count(data[:1000])    # FIRST 1000 chars only
    if token_count == 0: return False
    if len(data[:1000]) / token_count < 2 and len(data) > 100: return False   # :78 — minified (token density)
...
def conditional_hash(contents):                         # :92
    if len(contents) > 255: return md5(contents.encode()).hexdigest()
    return contents                                      # short content IS its own key
def file_path_to_chunks(file_path):                      # :97
    content_hash = conditional_hash(file_path + file_contents)   # PATH+CONTENT identity
    if content_hash in chunk_cache: return chunk_cache[content_hash]
    chunks = chunk_code(file_contents, path=file_path)           # default MAX_CHARS=12000, coalesce=80
...
def dfs(file_path=directory):                            # :116
    if only_file_name in ("node_modules", ".venv", "build", "venv", "patch"): return
    if file_path in vis: return                          # symlink-cycle guard
    with os.scandir(file_path) as it:
        children = list(it)
        if len(children) > FILE_THRESHOLD: return       # :124 — PRUNE dirs with >240 children (not descended)
        ...
with multiprocessing.Pool(processes=multiprocessing.cpu_count() // 4) as pool:   # :145
    for chunks in tqdm(pool.imap(file_path_to_chunks, file_list), ...): all_chunks.extend(chunks)
```

**Flow:** file discovery is a recursive os.scandir DFS that skips dependency/build basenames by name (node_modules/.venv/build/venv/patch), guards symlink cycles with a visited set, and PRUNES any directory with more than FILE_THRESHOLD=240 children outright (generated dirs like dist/node_modules subtrees are dropped wholesale rather than filtered file-by-file; NotADirectoryError yields the file itself) → each surviving path passes the memoized filter ladder (diskcache keyed directory+file so re-runs skip stat/decode entirely): extension table → parent-directory table (exclude_dirs matches path parts[:-1] ONLY — a file literally named `tests.py` survives a "tests" exclusion, but `src/tests/x.py` does not) → anywhere-in-path table → size window (10 B … 240 kB) → isfile → decodable (fallback encodings) → no NUL bytes → average line length ≤ 200 → token-density check on the FIRST 1000 chars only (tiktoken; <2 chars/token with file >100 B ⇒ minified/generated) → chunking runs in a multiprocessing.Pool(cpu_count() // 4) over pool.imap, each worker reading the file fresh and calling chunk_code with DEFAULTS (MAX_CHARS = 60*200 = 12000 chars ≈ 200 lines, coalesce=80 — four times the annotation plane's 3000-char chunks, because index chunks must be self-contained search units, not prompt blocks) → results are cached under conditional_hash(PATH + CONTENTS): md5 when the combined string exceeds 255 chars, the raw string otherwise (short files get exact-match keys without hashing); a content change therefore invalidates exactly one cache entry while unchanged files across repos share nothing (path is in the key) → the single production consumer, prepare_lexical_search_index, wraps the whole thing in its OWN snippets_cache keyed by get_lexical_cache_key (basename_commit_CACHE_VERSION_seed) and feeds the result to prepare_index_from_snippets with a per-key tantivy cache_path — two cache layers: per-file chunks (content-addressed) and per-repo-index (commit-addressed).
**Invariant:** The corpus is defined by NEGATION: every rule is an exclusion, and the ladder order is cost-ordered (string suffix checks before stat, stat before decode, decode before tiktoken) so the expensive checks run on the fewest files. The 240-child prune is a recall sacrifice made explicit — huge generated directories contribute NOTHING to the index, which is correct for search quality but means a port indexing monorepos with big source trees must raise or remove it. Caching is two-tier by design: chunk cache keys include the PATH (so identical file contents in different repos do not collide) while the outer snippets cache keys on commit (so unchanged commits skip the walk entirely); a port that collapses the tiers either re-chunks every file per commit or risks cross-repo contamination. The filter memoization key (directory+file, NOT content) means a file that CHANGES content keeps its old inclusion verdict until the process restarts — acceptable because the outer commit-keyed cache already gates re-walks, but a port with live-editing use cases must key on mtime/content too.
**Probe:** No offline-runnable test covers this module at pin (import chain needs diskcache/tiktoken/loguru/tqdm; tests/ holds only live-API harness scripts — standing block). Deterministic probes executed at pin: `grep -rn 'directory_to_chunks\|file_path_to_chunks\|filter_file(' sweepai/ | grep -v Binary | grep -v 'def \|repo_parsing_utils.py'` → lexical_search.py:18 (import) + :234 (call) ONLY — single production consumer confirmed; `grep -n 'size > 240000 or size < 10' sweepai/core/repo_parsing_utils.py` → :56 only; `grep -n 'len(data\[:1000\]) / token_count < 2' sweepai/core/repo_parsing_utils.py` → :78 only; `grep -n 'FILE_THRESHOLD = ' sweepai/core/repo_parsing_utils.py` → :90 (=240); `grep -n 'node_modules' sweepai/core/repo_parsing_utils.py` → :118 only; `grep -n 'cpu_count() // 4' sweepai/core/repo_parsing_utils.py` → :145 only; `grep -n 'MAX_CHARS=AVG_CHAR_IN_LINE \* 200' sweepai/utils/code_validators.py` → :96,:606 (two chunk_code definitions — the :603 one is the one imported here); `grep -n 'AVG_CHAR_IN_LINE = ' sweepai/utils/code_validators.py` → :30 (=60).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "directory_to_chunks filter_file conditional_hash file_path_to_chunks prepare_lexical_search_index chunk_code", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// repo_parsing_utils.py (168L whole), code_validators.py:603-643/:30, lexical_search.py:185-250 at pin
// substituted — see verification.md pass 6.
```

## Verdict
Adopt the cost-ordered exclusion ladder (suffix → path-part → size → decode → binary → line-length → token-density-on-prefix) as the template for "is this file worth indexing" decisions, the 240-child directory prune as an explicit recall/latency trade, the two-tier cache split (content-addressed per-file chunks vs commit-addressed per-repo index), and Pool-imap chunking with stateless workers (each worker re-reads its file — nothing crosses the Pool boundary). Adapt: the size window (10 B … 240 kB), the 200-char average-line threshold, the 2 chars/token density floor, and the 1000-char density sample are tuned constants — recalibrate against your corpus; the default 12000-char chunk size should match your downstream scorer's unit (Sweep's tantivy index wants ~200-line units; the annotation plane deliberately uses 3000-char units for prompts — same chunker, different MAX_CHARS); the exclude_dirs parts[:-1] semantics (parent-only matching) is subtle and worth a test in any port. Omit: the __main__ demo clone of sweepai/sweep, the commented-out @file_cache decorator on directory_to_chunks (superseded by the explicit two-tier caches), and the dead `dir_file_count` scaffolding comment. Coverage caveat: no live direct test at pin; this module sits under EVERY search operation, so a silent behavior change here degrades retrieval quality fleet-wide without any error signal.
