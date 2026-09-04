<!-- capsule-v2 -->
# py-chunk-aggregation-merge — how do per-chunk JSON summaries become one final summary, and what survives a failed chunk?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the merge contract over chunk summaries — section extension semantics, dedup behavior, and the all-failed failure boundary?

## Section-block aggregation with per-chunk skip
**Path/Symbol:** `backend/app/main.py:process_transcript_background` (:219-327).
**Signature:** `async def process_transcript_background(process_id: str, transcript: TranscriptRequest, custom_prompt: str)` (FastAPI BackgroundTask).
**Data Shape:** `all_json_data: list[str]` (one serialized `SummaryResponse` per successful chunk) → single `final_summary` dict with fixed keys (`People`, `SessionSummary`, `CriticalDeadlines`, `KeyItemsDecisions`, `ImmediateActionItems`, `NextSteps`, `MeetingNotes`). Merge rule: every non-MeetingNotes section's `blocks` list is EXTENDED across chunks; MeetingNotes sections are appended once per unique title (first chunk's title wins; later chunks extend the matched section's blocks). No dedup of block content across overlapping chunks.

### Decisive source
```python
for key in final_summary:
    if key == "MeetingNotes" and key in json_dict:
        ...final_summary[key]["sections"].extend(json_dict[key]["sections"])...
    elif key != "MeetingName" and key in json_dict and isinstance(json_dict[key], dict) and "blocks" in json_dict[key]:
        if isinstance(json_dict[key]["blocks"], list):
            final_summary[key]["blocks"].extend(json_dict[key]["blocks"])
```

**Flow:** chunk loop → per-chunk `json.loads` inside try/except (a malformed chunk is LOGGED and skipped, never fails the run) → name backfill (`update_meeting_name` only when some chunk produced a `MeetingName`) → terminal status write.
**Invariant:** Success requires AT LEAST ONE chunk: empty `all_json_data` ⇒ `status="failed"` with error `"Summary generation failed: No chunks were processed successfully. Check logs for specific errors."` (:308). Partial success is a completed summary. The process row is keyed by meeting_id and reused across runs (`create_process` UPDATE-then-INSERT).
**Probe:** `grep -cF 'No chunks were processed successfully. Check logs' backend/app/main.py` → `1` (battery P3); `grep -c '_section_order' backend/app/main.py` → `3` (P4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "final_summary blocks extend MeetingNotes sections", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt extend-not-dedup merge + ≥1-chunk success bar; adapt section key set to your schema; omit FastAPI BackgroundTasks transport (use your host's task runner). Direct tests absent — coverage caveat recorded.
