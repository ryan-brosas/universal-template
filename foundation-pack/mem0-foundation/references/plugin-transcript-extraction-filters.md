<!-- capsule-v2 -->
# Transcript JSONL extraction filters — which lines of an agent transcript become memory candidates?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** given an append-only agent transcript, how do you pick the small window of real conversation worth persisting?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/on_pre_compact.py`: `tail_lines` (:56-69), `parse_transcript` (:72-136); `auto_capture.py`: `extract_recent_exchanges` (:64-108).
**Signature:** `tail_lines(filepath, n) -> list[str]`; `parse_transcript(lines) -> dict`; `extract_recent_exchanges(lines, max_exchanges=3) -> list[dict]`.
**Data Shape:** snapshot dict {user_messages[-30:], files_modified sorted set, bash_commands[-20:], last_assistant_text[:10000]}; capture messages [{role, content[:2000]}].

### Decisive source
```python
chunk_size = min(file_size, n * 4096)          # binary-seek tail, errors="replace"
f.seek(max(0, file_size - chunk_size))
...
if entry.get("isSidechain"): continue           # subagent noise
if entry.get("isCompactSummary"): continue      # compaction artifacts (capture path)
if text and len(text) > 10 and not text.startswith("<"):   # "<" = tool-result echo
if role == "assistant" and content.startswith("{"):       # tool-call-only message
    continue
result = messages[-(max_exchanges * 2):]        # last N user+assistant PAIRS
```

**Flow:** seek-tail read → per-line json.loads (tolerant) → role/type gate → noise gates (sidechain/compact-summary, min length 10 vs 20, "<"-prefix, "{"-assistant) → collect (Write|Edit file_paths into set; Bash commands; last assistant text) → cap windows.
**Invariant:** extraction NEVER raises on malformed lines (continue); file list is deduped+sorted for determinism; caps bound payload size regardless of transcript size; two thresholds exist because snapshots want breadth while infer-captures want substance.
**Probe:** `cd /mnt/hdd/utopia/inspo/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_auto_capture.py -q` plus deterministic grep `grep -n 'startswith("<")' integrations/mem0-plugin/scripts/on_pre_compact.py` (upstream ships no dedicated pre-compact suite — caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "mem0", qualified_name: "mem0.integrations.mem0-plugin.scripts.auto_capture.extract_recent_exchanges" });
```

## Verdict
Adopt the tail-read + noise-gate + capped-window recipe for any transcript-to-memory pipeline; adapt thresholds/caps to your payload budget; omit Claude-specific type strings after mapping them to your transcript schema.
