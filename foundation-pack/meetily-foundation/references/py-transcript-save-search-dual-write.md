<!-- capsule-v2 -->
# py-transcript-save-search-dual-write — how do raw transcripts and summarization inputs coexist in one SQLite file?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What are the two transcript representations, their write paths, and the search dedup rule across them?

## Segments table + whole-text table with transcripts-first search
**Path/Symbol:** `backend/app/db.py:save_meeting_transcript` (:389-410), `save_transcript` (:283-327), `search_transcripts` (:769-861); `main.py:save_transcript` endpoint (:511-548).
**Signature:** `async def save_meeting_transcript(self, meeting_id, transcript, timestamp, summary="", action_items="", key_points="", audio_start_time=None, audio_end_time=None, duration=None)`; `async def save_transcript(self, meeting_id, transcript_text, model, model_name, chunk_size, overlap)`.
**Data Shape:** `transcripts` rows = per-SEGMENT text + wall-clock `timestamp` + recording-relative `audio_start_time/audio_end_time/duration` (playback sync; all three optional). `transcript_chunks` = ONE row per meeting holding the FULL concatenated text actually sent to the LLM + params. Meeting id is generated client-side by the endpoint as `meeting-{epoch_millis}`; `save_meeting` REJECTS duplicates matching id OR title (`raise Exception("Meeting ... already exists")`).

### Decisive source
```python
cursor2 = await conn.execute("""
    SELECT m.id, m.title, tc.transcript_text
    FROM meetings m JOIN transcript_chunks tc ON m.id = tc.meeting_id
    WHERE LOWER(tc.transcript_text) LIKE ?
    AND m.id NOT IN (SELECT DISTINCT meeting_id FROM transcripts WHERE LOWER(transcript) LIKE ?)
```

**Flow:** recording save ⇒ one meetings row + N segment rows (no chunks row); summarize ⇒ chunks row upserted per meeting_id (UPDATE-else-INSERT under BEGIN/commit). Search runs BOTH LIKE queries, segments first, then whole-text ONLY for meetings with no segment hit, and builds ±100-char snippets with ellipses; chunk-row results carry `datetime.utcnow()` as a fallback timestamp.
**Invariant:** The 10MB transcript guard (`len > 10_000_000 ⇒ ValueError`) lives on the CHUNKS path only. Segment timestamps are display truth; chunk fallback timestamps are synthetic — never mix them for ordering.
**Probe:** battery P1/P2 pin the ollama size override + range-step split in the same module; retrieval anchor: `search_graph {"query":"search_transcripts matchContext"}` resolves `backend/app/db.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "search_transcripts matchContext audio_start_time", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-representation split (segments for playback, whole-text for LLM) and segments-first search dedup; adapt schema to your ORM; omit CORS/dev logging. Direct tests absent — coverage caveat recorded.
