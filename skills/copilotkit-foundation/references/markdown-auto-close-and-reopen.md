<!-- capsule-v2 -->
# markdown-auto-close-and-reopen

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-discord/src/auto-close-streaming.ts` (byte-twin: `channels-slack/src/auto-close-streaming.ts`)
- Symbol: `autoCloseOpenMarkdown` / `detectOpenContext` / `renderContextOpener`
- Lines: autoCloseOpenMarkdown :41-119 (scanBracketStack :128-179), detectOpenContext :221-254, renderContextOpener :293-303
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-discord.src.auto-close-streaming.autoCloseOpenMarkdown`

## Question
Mid-stream the buffer is an UNFINISHED markdown document — how do you keep every intermediate edit rendering correctly without corrupting the final committed message?

## Signature & Data Shape
```typescript
autoCloseOpenMarkdown(text: string): string;   // balanced copy; adds NOTHING once text is self-balanced
detectOpenContext(text: string): { fenceLang: string | null; inlineCode: boolean; brackets: string[] };
renderContextOpener(ctx: OpenMarkdownContext): string;  // prefix that makes a continuation chunk self-renderable
```

## Decisive Source Excerpt
```typescript
// A marker with no content after it is NOT closed — closing would produce a
// transient `****` which looks worse than `**`.
while (stack.length > 0) {
  const top = stack[stack.length - 1]!;
  const after = text.slice(top.index + top.marker.length);   // stored PUSH index,
  if (/^\s*$/.test(after)) stack.pop();                       // NOT lastIndexOf:
  else break;
}
```
The stored push index exists because `*` is a substring of `**`: `text.lastIndexOf("*")` could match the `*` inside a later `**` and wrongly classify `"*ab**"`'s open italic as empty. Closers are emitted in reverse stack order (innermost first) so structure nests; closers are inserted BEFORE trailing whitespace (`"**bold "` → `"**bold**"`, not `"**bold **"`).

## Flow
1. **Pair first, then detect:** complete ```` ```…``` ```` regions and paired inline backticks are masked with `\u0001N\u0001` / `\u0002N\u0002` sentinels BEFORE scanning, so markers inside opaque code never count.
2. A dangling open fence is closed only if it has REAL code content past the optional language line (`hasFenceCodeContent`: no newline yet ⇒ still just-opened, don't close).
3. Bracket stack scan toggles longest-marker-first (`**`,`__`,`~~` before `*`,`_`); leftover stack = unbalanced markers to close.
4. `detectOpenContext` mirrors this on the text BEFORE a chunk boundary; `renderContextOpener` returns fences exclusively (an open fence means all other markers are inside opaque code) — ```` ```python\n ````, else stacked bracket markers + optional lone backtick.
5. The pair is consumed by `ChunkedMessageStream`: closer per chunk via transform, re-opener prepended to continuations — when the agent later emits the real closer, auto-close adds nothing (no double-close in the committed message).

## Invariant
Idempotence on balanced input (already-balanced markdown passes through byte-unchanged) is what makes transient edits converge with the final committed text; markers inside fenced/inline code must never be closed or counted.

## Direct-Test Probe
- File: `packages/channels-discord/src/auto-close-streaming.test.ts`
- Lines: :16 already-balanced unchanged; :23 `**hello`→`**hello**`; :27 does NOT close empty `**`; :49 `*ab**` closes the italic under an empty bold; :67 closes dangling inline code

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"autoCloseOpenMarkdown detectOpenContext renderContextOpener","limit":10}'
```

## Verdict
Adopt sentinel-masking + push-index stack scanning + content-gated closing verbatim for any channel that renders markdown mid-stream. Adapt the marker vocabulary per host dialect (mrkdwn, WhatsApp `*bold*`). Omit nothing — the "don't close an empty marker" rule is the difference between polished streaming and flickering garbage.
