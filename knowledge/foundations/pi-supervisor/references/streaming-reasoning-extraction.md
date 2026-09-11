<!-- capsule-v2 -->
# Streaming reasoning extraction — how does partial JSON become live UI text without a JSON parser?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How is the `reasoning` value pulled from an INCOMPLETE streaming JSON string, and which escape/anchor cases must not break it?

## extractThinking (`src/index.ts`)
**Path/Symbol:** `src/index.ts:extractThinking` (:39-49).
**Signature:** `extractThinking(accumulated: string): string` — pure function over the accumulated stream text.
**Data Shape:** Input: partial-or-complete JSON text; output: unescaped reasoning prefix ('' when absent).

### Decisive source
```ts
const keyIdx = accumulated.indexOf('"reasoning"');
if (keyIdx === -1) return '';
const after = accumulated.slice(keyIdx + '"reasoning"'.length);
const openMatch = after.match(/^\s*:\s*"/);        // key MUST be followed by : "
if (!openMatch) return '';                          // e.g. "reasoningX" or non-string value
const content = after.slice(openMatch[0].length);
const closeIdx = content.search(/(?<!\\)"/);         // first UNESCAPED quote = end
const raw = closeIdx === -1 ? content : content.slice(0, closeIdx);  // no close yet = still streaming
return raw.replace(/\\n/g, ' ').replace(/\\"/g, '"').trim();
```

**Flow:** wired as the `onDelta` callback of every supervisor prompt call (`src/index.ts:280-287`): each delta re-extracts and pushes to the widget so users watch the judge think. Works identically on complete JSON (closing quote found) and truncated streams (no close ⇒ whole remainder).
**Invariant:** (1) The `^\s*:\s*"` anchor means a key like `"reasoning_level"` does NOT match (colon-quote check fails) — porters loosening this will extract from sibling keys. (2) The negative-lookbehind `(?<!\\)` is what makes embedded `\"` survive; JS regex lookbehind required. (3) Absence of closing quote is STREAMING, not error — never treat as malformed. (4) Escaped newlines render as spaces because widget lines are single-line.
**Probe:** `tests/parsing.test.ts` — `returns empty string when no reasoning key` (:245), `extracts reasoning from streaming partial JSON (no closing quote)` (:261), `extracts reasoning with spaces around colon` (:267), `handles escaped newlines in reasoning` (:279), `handles escaped quotes in reasoning` (:287).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractThinking reasoning streaming delta", limit: 8 });
```

## Verdict
Adopt anchor+unescaped-quote scanning for any live view into streaming JSON. Adapt the key name. Omit nothing — 11 lines, fully portable.
