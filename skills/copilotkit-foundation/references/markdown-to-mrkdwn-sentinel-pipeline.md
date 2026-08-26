<!-- capsule-v2 -->
# markdown-to-mrkdwn-sentinel-pipeline

## Source
- Repo: `copilotkit`
- Path: `packages/channels-slack/src/markdown-to-mrkdwn.ts`
- Symbol: `markdownToMrkdwn`
- Lines: 20-75
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-slack.src.markdown-to-mrkdwn.markdownToMrkdwn`

## Signature & Data Shape
```typescript
export function markdownToMrkdwn(input: string): string;
```

## Decisive Source Excerpt
```typescript
export function markdownToMrkdwn(input: string): string {
  if (!input) return input;

  // ── 1. Pull code regions and tables out so we don't touch them. ──
  const codeRegions: string[] = [];
  const codePlaceholder = (i: number) => `\x00CODE${i}\x00`;

  let body = input.replace(/```[\s\S]*?```/g, (match) => {
    codeRegions.push(match);
    return codePlaceholder(codeRegions.length - 1);
  });
  body = body.replace(/`[^`\n]*`/g, (match) => {
    codeRegions.push(match);
    return codePlaceholder(codeRegions.length - 1);
  });

  // GFM-style tables: wrap in a fence with column-aligned cells so they
  // render as a readable monospace table rather than a pile of pipes.
  body = body.replace(
    /(^\|[^\n]+\|\s*\n\|[\s:|-]+\|\s*\n(?:\|[^\n]+\|\s*\n?)+)/gm,
    (table) => {
      const fenced = "```\n" + alignTable(table.trimEnd()) + "\n```";
      codeRegions.push(fenced);
      return codePlaceholder(codeRegions.length - 1);
    },
  );

  // ── 2. Bold first, into a sentinel; then italic won't eat its output. ──
  const BOLD_OPEN = "\x01";
  const BOLD_CLOSE = "\x02";
  body = body.replace(/\*\*([^\n*]+?)\*\*/g, `${BOLD_OPEN}$1${BOLD_CLOSE}`);
  body = body.replace(/__([^\n_]+?)__/g, `${BOLD_OPEN}$1${BOLD_CLOSE}`);

  // Headings (#…) → bold (also sentinel-marked).
  body = body.replace(
    /^\s{0,3}#{1,6}\s+(.*)$/gm,
    (_m, text: string) => `${BOLD_OPEN}${text.trim()}${BOLD_CLOSE}`,
  );

  // Strikethrough ~~text~~ → ~text~
  body = body.replace(/~~([^\n~]+?)~~/g, "~$1~");

  // Italic *text* or _text_ → _text_
  body = body.replace(/\*([^\n*]+?)\*/g, "_$1_");
  body = body.replace(/(?<!\w)_([^\n_]+?)_(?!\w)/g, "_$1_");

  // Bold sentinels → *text*
  body = body.replace(new RegExp(BOLD_OPEN, "g"), "*");
  body = body.replace(new RegExp(BOLD_CLOSE, "g"), "*");

  // Links [text](url) → <url|text>
  body = body.replace(/\[([^\n[\]]+?)\]\((https?:\/\/[^\s)]+)\)/g, "<$2|$1>");

  // ── 3. Put code regions and tables back in. ──
  body = body.replace(/\x00CODE(\d+)\x00/g, (_m, i) => codeRegions[Number(i)] ?? "");

  return body;
}
```

## Flow
1. Phase 1: Extract code fences, inline code snippets, and GFM markdown tables into placeholder tokens (`\x00CODE{i}\x00`).
2. Phase 2: Convert bold syntax (`**`, `__`) and headings (`#`) into sentinel characters (`\x01`, `\x02`).
3. Phase 3: Convert strikethrough, italic (`*`, `_`), and links (`[text](url)` to `<url|text>`).
4. Phase 4: Replace bold sentinels with Slack `*text*` tokens (preventing italic transforms from corrupting bold text).
5. Phase 5: Re-inject preserved code and table blocks.

## Invariant
Markdown formatters targeting Slack `mrkdwn` must protect code and table blocks first, and use sentinel substitution between bold and italic passes to avoid recursive regex destruction of asterisks.

## Direct-Test Probe
- File: `packages/channels-slack/src/markdown.test.ts`
- Lines: 25-80
- Suite: `describe("markdownToMrkdwn")`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"markdownToMrkdwn BOLD_OPEN alignTable"}'
```

## Verdict
Adopt the multi-pass sentinel markdown-to-mrkdwn converter and monospace table alignment pipeline.
