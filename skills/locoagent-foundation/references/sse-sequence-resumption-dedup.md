<!-- capsule-v2 -->
# SSE sequence resumption + dedup — how does a reconnecting event stream resume exactly where it stopped without replaying the whole session?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What state must a transport carry across instances so a swap resumes from the right sequence number, and how are server duplicates handled in-memory?

## High-water mark seeding + bounded seen-Set pruning
**Path/Symbol:** `src/cli/transports/SSETransport.ts`: ctor seed (:209-215), `getLastSequenceNum`/:227-229, connect resumption params (:244-266), dedup+prune in readStream (:353-383), `parseSSEFrames`/:52-116.
**Signature:** ctor `(url, headers?, sessionId?, refreshHeaders?, initialSequenceNum?, getAuthHeaders?)`; frames `{event?, id?, data?}`.
**Data Shape:** `lastSequenceNum` monotonic high-water mark; sent as BOTH `?from_sequence_num=` query param AND `Last-Event-ID` header; `seenSequenceNums: Set<number>` pruned when size >1000 down to entries ≥ high-water−200.

### Decisive source
```ts
// Seed so the FIRST connect() sends from_sequence_num / Last-Event-ID.
// Without this a fresh SSETransport always replays from 0 — the entire
// session history on every transport swap.
if (initialSequenceNum !== undefined && initialSequenceNum > 0) this.lastSequenceNum = initialSequenceNum
// per frame:
if (this.seenSequenceNums.has(seqNum)) { /* duplicate warn */ }
else { this.seenSequenceNums.add(seqNum);
  if (this.seenSequenceNums.size > 1000) {
    const threshold = this.lastSequenceNum - 200   // only near-head seqs matter for dedup
    for (const s of this.seenSequenceNums) if (s < threshold) this.seenSequenceNums.delete(s)
  } }
if (seqNum > this.lastSequenceNum) this.lastSequenceNum = seqNum
```
Callers recreate transports on work events: read `getLastSequenceNum()` BEFORE close() and pass it as the next instance's `initialSequenceNum`.

**Flow:** connect builds URL+headers from high-water → stream parsed incrementally by `parseSSEFrames` (double-newline frames; `:comment` lines count as liveness proof and emit a frame; multi `data:` lines join with \n; one space after colon stripped per SSE spec) → every frame resets the 45s liveness timer → ids update dedup set + high-water → `client_event` payloads re-emitted as NDJSON for StructuredIO consumers.
**Invariant:** Resumption identity lives OUTSIDE the instance (caller-mediated handoff); dedup memory is bounded because only near-head sequence numbers can recur after reconnect. Cookie auth removes stale Authorization header ("sending both confuses the auth interceptor").
**Probe:** `grep -n "from_sequence_num" src/cli/transports/SSETransport.ts` (`:247`), `grep -n "threshold = this.lastSequenceNum - 200" src/cli/transports/SSETransport.ts` (`:372`), `grep -n "initialSequenceNum > 0" src/cli/transports/SSETransport.ts` (`:213`), `grep -n "isComment = true" src/cli/transports/SSETransport.ts` (`:80`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "SSETransport lastSequenceNum parseSSEFrames resumption", limit: 5 });
```

## Verdict
Adopt caller-mediated high-water handoff and threshold-pruned dedup. Adapt param/header names to your server contract. Omit the seen-set only if your server guarantees exactly-once redelivery.
