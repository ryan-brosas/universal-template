<!-- capsule-v2 -->
# Streaming thinking extractor — pulling partial reasoning text out of a still-streaming JSON response

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you show live "thinking" text from a JSON-only response before the response completes?

## Key-anchored scan with escape-aware terminator
**Path/Symbol:** `src/index.ts:39-49` (`extractThinking`), wired as the `onDelta` callback in the settled handler :280-288.
**Signature:** `extractThinking(accumulated: string): string`.
**Data Shape:** Input = raw accumulated stream text (possibly mid-string, no closing quote); output = unescaped reasoning text or `''`.

### Decisive source
```ts
export function extractThinking(accumulated: string): string {
  const keyIdx = accumulated.indexOf('"reasoning"');
  if (keyIdx === -1) return '';
  const after = accumulated.slice(keyIdx + '"reasoning"'.length);
  const openMatch = after.match(/^\s*:\s*"/);
  if (!openMatch) return '';
  const content = after.slice(openMatch[0].length);
  const closeIdx = content.search(/(?<!\\)"/);   // first UNESCAPED quote ends the value
  const raw = closeIdx === -1 ? content : content.slice(0, closeIdx);
  return raw.replace(/\\n/g, ' ').replace(/\\"/g, '"').trim();
}
```

**Flow:** every text delta → re-scan the WHOLE accumulated buffer → find `"reasoning"` key → require an opening `": "` → take everything up to the first non-backslash-escaped quote (or everything if still streaming) → unescape newlines/quotes → widget shows it live.
**Invariant:** The negative lookbehind `(?<!\\)"` is load-bearing: escaped quotes inside the reasoning must not terminate it. Absence of a closing quote is the STREAMING case and returns the partial content — this is why re-scanning the full accumulation each delta works. No JSON.parse is attempted; the function tolerates arbitrarily truncated JSON.
**Probe:** `grep -cF 'closeIdx === -1 ? content : content.slice(0, closeIdx)' src/index.ts` → 1; `grep -cn '(?<!\\\\)"' src/index.ts` → 1. Direct tests: `tests/parsing.test.ts:244-267+` ("returns empty string when no reasoning key", "extracts reasoning from complete JSON", "extracts reasoning from streaming partial JSON (no closing quote)", "extracts reasoning with spaces around colon").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractThinking reasoning stream accumulated", limit: 10 });
```

## Verdict
Adopt key-anchored escape-aware scanning for any live-preview of a field inside a streaming JSON payload. Adapt the key name to your schema (`reasoning` here). Omit nothing — replacing the lookbehind with a plain quote search is the classic wrong port that truncates at the first quoted word.
