<!-- capsule-v2 -->
# Feed sanitization grammar — what gets normalized before any event line is persisted or rendered?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How are agent names, targets, and previews cleaned so one-line feed rendering can never break?

## Inline vs preview whitespace policies
**Path/Symbol:** `feed/index.ts:sanitizeInlineText` (:82-91), `sanitizePreview` (:93-98), `sanitizeAgentName` (:100-102), `sanitizeFeedEvent` (:104-113), applied in `parseEventLine` (:115-128) AND `appendFeedEvent` (:185-204).
**Signature:** `sanitizeFeedEvent(event: FeedEvent): FeedEvent`.
**Data Shape:** inline: CR/LF/TAB → space, `\s+ → ' '`, trim; preview: PRESERVES newlines (`\r→\n`, tab→space, multi-space collapse); empty ⇒ undefined.

### Decisive source
```ts
function sanitizePreview(value?: string): string | undefined {
  if (!value) return undefined;
  // Preserve newlines for multi-line previews, but normalize other whitespace
  const normalized = value.replaceAll('\r', '\n').replaceAll('\t', ' ').replace(/ +/g, ' ').trim();
  return normalized.length > 0 ? normalized : undefined;
}
```
```ts
// formatFeedLine flattens previews for the ONE-LINE feed view at render time
const normalizedPreview = rawPreview?.replace(/\n/g, ' ');
... length > 90 ? slice(0, 87) + '...' : ...
```

**Flow:** every append AND every parse passes through the same sanitizer (defense on write + tolerance on read of foreign lines), so stored bytes are already clean; channel field re-normalized to id form. The renderer then independently flattens newlines and ellipsizes at 90 chars — storage keeps structure, presentation truncates.
**Invariant:** Two distinct whitespace contracts for two fields: target/agent must be single-line (they join line grammar), previews may keep paragraph shape for detail views. Unknown agent becomes literal `'unknown'`, never dropped.
**Probe:** direct tests `tests/feed.test.ts::readFeedEvents caches by mtime and size until file changes` + sanitize assertions (`grep -n "sanitize" tests/feed.test.ts | head -5`); `grep -c "replaceAll('\\\\r', '\\\\n')" feed/index.ts` (=1); `grep -n "slice(0, 87)" feed/index.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "sanitizeFeedEvent sanitizeInlineText sanitizePreview formatFeedLine", limit: 5 });
```

## Verdict
Adopt dual-policy sanitization (inline-flatten vs newline-preserving previews) applied on both write and read; adapt limits; keep the unknown-agent sentinel rather than dropping events.
