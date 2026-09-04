<!-- capsule-v2 -->
# Transcript turn parser — how do you read speaker turns, WebVTT cues, and header blocks without misclassifying lines?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does TranscriptLoader distinguish headers from all-caps speaker turns and VTT identifiers from payload lines?

## TranscriptLoader
**Path/Symbol:** `ingestion/src/zep_ingest/loaders/transcript.py:51` (`TranscriptLoader`), `:121` (`_split_headers`), `:149` (`_match_header`), `:169` (`_parse_turns`), `:216` (`_is_vtt_identifier`), `:234` (`_resolve_start`), `:252` (`_chunk`). DEFAULT_CHUNK_CHARS=3_500.
**Signature:** `_match_header(line) -> Match | None`; `_is_vtt_identifier(lines, index) -> bool`; meeting_start requires tz; single file only when meeting_start given.
**Data Shape:** `_Turn(speaker, text, offset: timedelta|None)`; episode created_at = resolved_start + first-turn offset (None if start unknown); metadata source_type=transcript, meeting=title[:100], chunk=i/total.

### Decisive source
```python
# _match_header — a header and an all-caps turn are the SAME shape
# ("DATE: 2024-06-15" vs "ALICE: First turn"); the key settles it:
#   no value ⇒ header (a turn requires text after the colon);
#   otherwise every key word must be in the metadata vocabulary.
# The vocabulary stays narrow because the two mistakes are NOT symmetric:
# reading a turn as a header consumes the rest of the header block and can
# empty the file, while reading a header as a turn only leaves one extra
# line of text in the episode.
# Role words that double as speakers — HOST, SPEAKER, INTERVIEWER —
# deliberately absent from _HEADER_KEYS.

# _is_vtt_identifier — qualifies only if directly ABOVE the timing line AND
# below the blank line ending the previous cue. Skipping blanks to find the
# timing line satisfies neither: the last payload line of a cue is also
# followed — after a blank — by the next cue's timing line, so it would be
# read as that cue's identifier and dropped, "which empties all but the
# final turn of any file written without them".
```

**Flow:** split leading header block (stops at first timestamp/cue/bold turn; `---` and blanks skipped; `# ...transcript` heading dropped) → scan body: `[hh:mm:ss]` markers and VTT cue lines set the running offset; `<v Name>` voice tags / `**Name:**` bold / `Name:` plain become turns; continuation lines append to the previous turn → chunk by rendered size (speaker+text+3) at 3,500 chars → render inline as `Speaker: text` so attribution survives plain-text ingestion.
**Invariant:** Asymmetric error costs drive classifier strictness. Timestamps resolve to offsets RELATIVE to meeting start (from arg, DATE header + default_start_time with warning, or filename date) — never wall-clock guesses.
**Probe:** `grep -c 'def test' ingestion/tests/test_transcript_loader.py` → ≥10 incl. VTT identifier cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "TranscriptLoader parse turns vtt identifier header", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt vocabulary-narrowed header matching + position-strict VTT identifiers + offset-based timestamps; adapt regexes to your transcript dialects; omit Zep metadata keys.
