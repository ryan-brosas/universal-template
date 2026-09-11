<!-- capsule-v2 -->
# Streaming tag splitter — how do you route `<tag>...</tag>` regions out of a token stream without buffering it all?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you separate reasoning-tag content (e.g. `<think>`) from surrounding text incrementally, char-by-char, when tags may be split across chunks and nested?

## Three-state char machine with depth counting + same-class chunk coalescing
**Path/Symbol:** `src/utils/tag-matcher.ts` (`TagMatcher` class :12-111; states TEXT/TAG_OPEN/TAG_CLOSE :17; `_update` :51-98; `collect` :25-31 coalescing; public `update` :107-109 + `final(chunk?)` :100-105).
**Signature:** `new TagMatcher(tagName: string, transform?: (chunks: TagMatcherResult) => Result, position = 0)`; `update(chunk): Result[]`; `final(chunk?): Result[]`.
**Data Shape:** Output = ordered `TagMatcherResult[]` = `{data, matched}[]` — `matched:true` runs are inside the tag region; adjacent same-matched fragments are merged into one chunk (`collect()` joins onto `last` when `matched` class matches).

### Decisive source
```ts
if (this.state === "TAG_OPEN") {
    if (char === ">" && this.index === this.tagName.length) {
        this.state = "TEXT"
        if (!this.matched) this.cached = []   // OPENING tag itself is DISCARDED from output
        this.depth++; this.matched = true
    } else if (this.index === 0 && char === "/") this.state = "TAG_CLOSE"
    else if (char === " " && (this.index === 0 || this.index === this.tagName.length)) continue // tolerate < think >
    else if (this.tagName[this.index] === char) this.index++
    else { this.state = "TEXT"; this.collect() }  // mismatch → emit buffered chars as text
}
// TAG_CLOSE mirrors this; on match: depth--, matched = depth > 0   ← NESTING via counter
```
The `position` constructor arg gates where a tag MAY open (`pointer <= position + 1`) — used to ignore tags before a stream offset.

**Flow:** chars accumulate in `cached` buffer → `<` enters TAG_OPEN (only at allowed positions) → name mismatch anywhere falls back to TEXT and flushes the buffer as ordinary text → full `<tag>` match discards the marker and flips matched-on with depth++ → inner text collects under matched=true → `</tag>` decrements; only when depth hits 0 does matched flip off and the closing marker get dropped → `final()` flushes any pending buffer.
**Invariant:** Every input character is either emitted in exactly one output chunk or consumed as part of a discarded marker — no loss, no duplication; markers split across arbitrary chunk boundaries still parse because state persists across `update()` calls; nesting is handled by depth, not by recursion.
**Probe:** No dedicated spec file at this HEAD for TagMatcher itself — behavior pinned transitively by provider-stream consumers (think-tag routing) and the deterministic char-machine contract above; coverage caveat recorded here per gate rules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "TagMatcher streaming tag think", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the char-state-machine wholesale (it is ~100 lines and host-free); adapt the transform hook to your event types. Do NOT replace with regex-on-full-buffer — the entire point is bounded memory over unbounded streams and split-marker tolerance.
