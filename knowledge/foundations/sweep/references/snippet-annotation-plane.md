<!-- capsule-v2 -->
# Snippet annotation plane — how do you attach per-block code summaries to planning-prompt snippets, and which of its cache/parallelism/reassembly choices are load-bearing?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How does Sweep turn raw snippet text into annotated `<original_code>`/`<code_summary>` pairs for the planning prompts — chunking, per-chunk LLM annotation, parallelism, caching, failure posture — and where does the reassembly break?

## get_annotated_source_code + format_snippets: tree-sitter chunks → 4-worker haiku annotations → first-occurrence string reassembly
**Path/Symbol:** `sweepai/core/annotate_code_openai.py:get_annotated_source_code` (:96–135), `AnnotateCodeBot.annotate_code` (:48–91), `process_chunk` (:93–95); `sweepai/core/sweep_bot.py:format_snippets` (:371–395); chunker `sweepai/utils/code_validators.py:chunk_code` (:603–643, AVG_CHAR_IN_LINE=60 at :30). **Live callers:** format_snippets ← `get_files_to_change` (:449 initial render, :528 post-renames rebuild) and `get_files_to_change_for_gha` (:757/:843); plus the DEAD `get_files_to_change_for_test` (:1230, see test-editing-variant-plane).
**Signature:** `get_annotated_source_code(source_code: str, issue_text: str, file_path: str) -> tuple[str, list[str]]` (annotated source, per-chunk summary strings); `format_snippets(relevant_snippets, read_only_snippets, problem_statement) -> str` (one `<relevant_files>` message block).
**Data Shape:** input = FULL file content + issue text + path; output = same content with each ≤3000-char tree-sitter chunk wrapped in an `<original_code>`/`<code_summary>` pair; failure shape = placeholder summary text, never an exception.

### Decisive source
```python
@file_cache(ignore_params=["issue_text"]) # safe to cache
def get_annotated_source_code(source_code: str, issue_text: str, file_path: str):
    annotated_source_code = source_code
    code_chunks = chunk_code(source_code, file_path, MAX_CHARS=60 * 50)          # 3000 chars, tree-sitter
    code_contents = [chunk.get_snippet(False, False) for chunk in code_chunks]
    if NUM_WORKERS > 1:                                                          # NUM_WORKERS = 4
        pool = multiprocessing.Pool(processes=NUM_WORKERS)
        results = [pool.apply_async(process_chunk, args=(idx, code_content, source_code, issue_text, file_path)) ...]
        ...
        for result in results:
            idx, formatted_code_content, formatted_annotation = result.get()
            code_with_summary = f"{formatted_code_content + formatted_annotation}"
            annotated_source_code = annotated_source_code.replace(code_contents[idx], code_with_summary, 1)
    # AnnotateCodeBot.annotate_code — ANY exception ⇒ "" ⇒ placeholder, ticket never blocks
    except Exception as e:
        logger.warning(f"AnnotateCodeBot failed with error: {e}")
        return ""
    if not annotation:
        annotation = "No summary was provided for this code block."
    formatted_code_content = f'<original_code file_path="{file_path}" index="{idx}">\n' + code_content + "\n</original_code>\n"
    formatted_annotation   = f'<code_summary file_path="{file_path}" index="{idx}">\n' + annotation + "\n</code_summary>\n"
```

**Flow:** format_snippets iterates tqdm(relevant_snippets + read_only_snippets) — BOTH lists rendered with the SAME `<relevant_file>` template (read-only snippets are labeled relevant_file in the prompt) → per snippet, get_annotated_source_code on snippet.get_snippet(add_lines=False) → chunk_code splits the FULL file into ≤3000-char (60*50) tree-sitter chunks (naive line-based fallback, line_count = MAX_CHARS // 60, for unknown extensions; each Snippet carries content=full code with start/end delimiting its range) → each chunk is annotated by a FRESH AnnotateCodeBot().annotate_code → chat_anthropic(model="claude-3-haiku-20240307", temperature=0.2, verbose=False) with a two-part prompt (whole source_code as context + issue + the single code_to_annotate block) expecting `<analysis>` + `<code_annotation>` tags; only the code_annotation group is kept → 4-worker multiprocessing.Pool (comment: "tune based on haiku rate limit"), results collected in submission order → reassembly wraps each chunk as `<original_code file_path index>` + `<code_summary file_path index>` pairs and splices them back via str.replace(chunk_text, wrapped, 1) → returns (annotated.strip("\n"), summaries). The whole function sits under @file_cache with issue_text EXCLUDED from the key.
**Invariant:** Annotation is a BEST-EFFORT enrichment: every failure mode (API error, empty tag, missing tag) degrades to the literal placeholder "No summary was provided for this code block." — the ticket must never block or crash on annotation. The cache key is (source_code, file_path) ONLY because issue_text is ignored — annotations for a given file version are shared across ALL issues, so the prompt's claim that summaries help solve THIS issue is only true by luck of the first annotating issue; a port that wants issue-specific summaries must include the issue in the key (and pay for it). The reassembly uses str.replace(count=1) on the chunk TEXT, not on offsets: when two chunks contain identical text, the idx-th replacement lands on the FIRST occurrence — annotations can be attached to the wrong chunk. A port must splice by offset/range (the Snippet start/end are already available), not by text search. The multiprocessing branch means each worker constructs its own ChatGPT client (no shared state crosses the Pool boundary) — any per-process memoization does not carry into workers.
**Probe:** No offline-runnable test exists for annotate_code_openai or format_snippets at pin (standing finding; import chain needs anthropic/openai/redis/tree-sitter). Deterministic probes executed at pin: `grep -rn 'ignore_params=\["issue_text"\]' sweepai/` → annotate_code_openai.py:95 only; `grep -n 'MAX_CHARS=60 \* 50' sweepai/core/annotate_code_openai.py` → :98 only; `grep -n 'NUM_WORKERS' sweepai/core/annotate_code_openai.py` → :12 (=4),:101,:102; `grep -n 'CLAUDE_MODEL = ' sweepai/core/annotate_code_openai.py` → :11 ("claude-3-haiku-20240307"); `grep -n 'temperature=0.2' sweepai/core/annotate_code_openai.py` → :69 only; `grep -rn 'No summary was provided' sweepai/` → :90 (process_chunk) + :126 (sequential branch); `grep -n 'annotated_source_code.replace' sweepai/core/annotate_code_openai.py` → :115 (pool branch, code_contents[idx]) + :130 (sequential branch, code_content); `grep -n 'format_snippets(' sweepai/core/sweep_bot.py` → def :371 + calls :449,:528,:757,:843 (live planner ×2 incl. post-renames rebuild, GHA variant ×2); `grep -rn 'chunk_code(' sweepai/` → def code_validators.py:603 + repo_parsing_utils.py:102 (default MAX_CHARS) + annotate_code_openai.py:98 (MAX_CHARS=3000).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "get_annotated_source_code AnnotateCodeBot format_snippets chunk_code code_summary original_code", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// annotate_code_openai.py (138L whole), sweep_bot.py:371-395, code_validators.py:603-643 at pin
// substituted — see verification.md pass 5.
```

## Verdict
Adopt the fail-soft annotation posture (any per-chunk failure degrades to an explicit placeholder string, never an exception — the planning pipeline must survive total annotation outage), the cheap-model-per-chunk split (haiku temp 0.2 for summaries while the planner runs opus/gpt-4o), the whole-file-as-context + single-block-to-annotate prompt shape, and the explicit `<original_code>`/`<code_summary>` paired-tag output grammar that downstream prompts can rely on. Adapt: splice annotations back by Snippet start/end OFFSETS instead of str.replace-on-text (identical chunks mislabel under count=1 replacement); decide deliberately whether the cache key includes the issue (Sweep excludes it — cross-issue sharing is a cost win and a correctness loss); keep workers stateless since nothing crosses the Pool boundary. Omit: rendering read-only snippets under the relevant_file template (mislabels context for the model), the tqdm progress bars (format_snippets loop and the sequential annotation branch — noise in a cached/worker path), and the __main__ demo call with empty strings. Coverage caveat: no live direct test at pin; the four live call sites (two planners × initial+post-renames) mean a change here alters every planning prompt.
