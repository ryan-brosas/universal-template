<!-- capsule-v2 -->
# Stream tag scanner — how do you parse `<think>`/`<code>`-style tags incrementally over a token stream without rescanning, fragmenting, or re-detecting your own start tag?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When special tags arrive split across arbitrary SSE chunk boundaries, how do I convert them into structured output items exactly once each?

## Incremental scanner with per-item scan memory
**Path/Symbol:** `backend/open_webui/utils/middleware.py:tag_output_handler` (closure inside `streaming_chat_response_handler`, 3792-4049).
**Signature:** `def tag_output_handler(content_type, tags, output) -> tuple[output, end_flag]`.
**Data Shape:** `output` is the OR-style item list (`message` | `reasoning` | `open_webui:code_interpreter` | `_tag_type` message); `tags` is `[(start_tag, end_tag), ...]`; scan memory is a dict keyed `(item_id, content_type) → scanned char count`.

### Decisive source
```python
scanned_length = get_scanned_length(item, item_text)
max_start_tag_length = max((len(start_tag) for start_tag, _ in tags), default=1)
search_start = max(0, scanned_length - max_start_tag_length + 1)

if scanned_length and any(
    start_tag.startswith('<') and start_tag.endswith('>') for start_tag, _ in tags
):
    last_tag_boundary = max(
        item_text.rfind('>', 0, scanned_length),
        item_text.rfind('\n', 0, scanned_length),
    )
    open_tag_start = item_text.rfind('<', 0, scanned_length)
    if open_tag_start > last_tag_boundary:
        search_start = min(search_start, open_tag_start)
```
(middleware.py 3860-3873)

**Flow:** resume scanning at `scanned − longest_start_tag + 1` (a full tag can straddle the last-resume boundary) → if an unterminated `<` sits past the last `>`/`\n` boundary, widen the window back to it (partial `<thin|`) → on a start-tag match: clear scan memory, truncate the prefix message to pre-tag text (dropping it entirely when whitespace-only), append a typed in-progress item carrying `start_tag`/`end_tag`/parsed attributes → end-tag path: search the tagged item's own content from its own scan offset; on match strip both tags, complete the item (`status: completed`, duration for reasoning; `code` field for code_interpreter) and append a FRESH message item holding any leftover post-end-tag text; no match yet ⇒ save the new scanned length and wait.
**Invariant:** each start tag is detected exactly once per stream. The guard that makes this hold lives at the delta-consumption site: while the last output item is an in-progress tagged block (`reasoning`, `open_webui:code_interpreter`, or a message with `_tag_type` set — explicitly excluding `attributes.type == 'reasoning_content'`), incoming text is appended INTO that item instead of creating a new message, "otherwise tag_output_handler re-detects the start tag on every chunk and fragments the output" (middleware.py 4681-4730). A code-interpreter end tag sets `end_flag`, which breaks the outer SSE loop immediately.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "search_start = max(0, scanned_length" backend/open_webui/utils/middleware.py` → 3862; `grep -n "inside_tag_block = (" backend/open_webui/utils/middleware.py` → 4690; `sed -n '3892,3895p' backend/open_webui/utils/middleware.py` shows the empty-prefix-message pop.

## Get live surrounding code
**Retrieve:** `tag_output_handler`, `queue_pending_delta_data`, and their sibling helpers are CLOSURES inside `streaming_chat_response_handler`, so they are not separate graph nodes — a naive query on their names MISSES (observed: drifts to swagger-ui/flush noise). Target the enclosing handler instead:
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "streaming_chat_response_handler tool call iterations while loop", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `streaming_chat_response_handler` 3750-5653; read the cited line ranges from source.

## Verdict
Adopt: resume-offset scanning bounded by longest-tag length, the open-bracket backtrack for tags split mid-token, typed-item conversion with leftover-text splicing into a fresh message, and the inside-block append guard as the single source of "already inside a tag" truth. Adapt the OR-style item vocabulary and attribute regex to your schema. Omit open-webui's specific tag catalog (reasoning/solution/code_interpreter) and its SSE loop integration. Coverage caveat: middleware.py is graph-clean but has no upstream test; claims pinned by direct source reads at lines cited above.
