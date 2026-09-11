<!-- capsule-v2 -->
# Slack thread grouping & episode shaping — what is the semantic unit, and how do timestamps and duplicates behave?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How are messages grouped into episodes, ordered, deduped, and stamped for fact-validity timelines?

## Thread grouping / _parse / _episode
**Path/Symbol:** `ingestion/src/zep_ingest/loaders/slack.py:554` (`_load_conversation`), `:592` (`_parse`), `:666` (`_normalize_text`), `:675` (`_episode`).
**Signature:** grouping = "thread" (default) | "message"; episodes carry `created_at = datetime.fromtimestamp(float(first.ts), tz=UTC).isoformat()`.
**Data Shape:** Episode metadata: source_type=slack, channel=label, conversation_type=kind, `thread_ts` present when len>1 OR first message carries thread_ts (lone reply whose parent was filtered still belongs to a thread).

### Decisive source
```python
# _load_conversation — per-conversation duplicate defense:
if message.ts in seen_ts:
    self._duplicate_ts += 1
    continue
...
messages.sort(key=lambda m: float(m.ts))
# thread key preserves first-appearance order; final ordering by float ts:
threads[key].append(message)
for key in sorted(order, key=float):
    yield self._episode(threads[key], conversation)

# _parse — a bad ts must drop ONE message, not abort the export:
try:
    float(ts)
except (TypeError, ValueError):
    self._invalid_ts += 1
    return None
```

**Flow:** day files read in sorted order → parse (skip subtypes incl. channel_join/leave; bot gate keys on bot_id OR subtype=="bot_message" — webhook posts often have only the subtype) → normalize markup (@mentions→names via roster, channel refs, links "label (url)", html.unescape) → blank text dropped → numeric-ts validation → sort by epoch → group by thread_ts-or-own-ts preserving insertion order → emit one episode per thread sorted by thread start.
**Invariant:** created_at comes from the ORIGINAL Slack epoch timestamp ("so backfilled facts carry the correct valid_at timeline") — never ingestion time. Duplicates within a conversation (merged dumps) are skipped WITH a count warning; invalid ts skips the single message with a warning that says the export "has been altered or is corrupt". Ordering by float(ts), not string.
**Probe:** `grep -c 'def test' ingestion/tests/test_slack_loader.py` → 82; thread/duplicate/bot cases pinned there.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "SlackExportLoader thread grouping normalize mention episode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt thread-as-unit grouping + original-timestamp stamping + counted duplicate/ts defenses; adapt formatter output shape to your graph's needs; omit Slack-specific regexes.
