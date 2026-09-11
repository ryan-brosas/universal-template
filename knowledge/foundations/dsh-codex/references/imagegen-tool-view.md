<!-- capsule-v2 -->
# Imagegen tool view — how should a tool-call view present generation results without trusting the result block's shape?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how does an inline conversation view parse structured markers out of plain tool-result text, load attachments through an injectable cached loader, and offer preview/open affordances that never break the transcript?

## Defensive result parsing and injectable image loading
**Path/Symbol:** `src/client/ImagegenToolView.tsx:40-66 resultParts`, `:68-70 argsRaw`, `:72-78 prettyJson`, `:80-86 promptSummary`, `:88-95 resultOutput`, `:97-159 GeneratedImage`, `:162-214 ImagegenToolView`, `src/client/index.tsx:42-56 loadImage` cache.
**Signature:** `function resultParts(block): { running: boolean; failed: boolean; image?: ImageAttachmentRef; path?: string; writeFailed: boolean; resultText: string }`; `type ImageLoader = (attachment: ImageAttachmentRef) => Promise<string>`; `export function ImagegenToolView(props: ToolCallViewProps & { loadImage: ImageLoader; t }` .
**Data Shape:** input is a host tool-result block (`kind === 'tool-result'`, `content[]` of `{type:'image',attachment}|{type:'text',text}`, `isError`, `call.argsRaw`); text is scanned for `<output_path operation="create|update">PATH</output_path>` and `<output_error>`; everything else stays opaque strings.

### Decisive source
```ts
let image: ImageAttachmentRef | undefined
let text = ''
for (const item of block.content) {
  if (item.type === 'image' && image === undefined) image = item.attachment
  else if (item.type === 'text') text += item.text
}
const path = text.match(/<output_path\s+operation="(?:create|update)">([^<]+)<\/output_path>/u)?.[1]
return {
  running: false,
  failed: block.isError,
  ...image === undefined ? {} : { image },
  ...path === undefined ? {} : { path },
  writeFailed: text.includes('<output_error>'),
  resultText: text,
}
```

**Flow:** block arrives → non-`tool-result` blocks render as running → first image attachment becomes THE preview, texts concatenate, path/error markers are regex-scanned out of the plain text → collapsed row shows tool name + prompt summary (parsed `prompt` field, else raw args) or `Generating…` only while running with an EMPTY summary, red `Generation failed` when `isError` → expanded panel pretty-prints IN args (raw fallback) and OUT (JSON re-projection naming attachment/outputPath/workspaceSave when an image exists) → GeneratedImage loads through the injected loader (attempt-count retry on failure), previews via portal with Escape close and focus returned to the opener → saved row renders the extracted path wired to host `openFile`.
**Invariant:** presentation degrades, never lies: missing/unparseable pieces fall back to raw text instead of crashing; "Generated; workspace save failed" shows ONLY when finished + no path + `<output_error>` present (a saved path suppresses it); the preview button opens only once `src` resolves; async loads guard a `live` flag so unmounted views never set state; the entry-side loader caches one promise per `${sessionId}:${attachmentId}` and revokes every object URL at teardown. Caveat recorded honestly then closed: no dedicated spec file exists, so a transient vitest probe (created against actual source, run, removed in the same pass — git stayed clean) verified 3/3: path extraction wired to `openFile('/w/fox.png')` with the note suppressed, `<output_error>` without a path shows the attachment-only note, and the Generating/'{}'-fallback/prompt/failure summary ladder renders as specified.
**Probe:** transient probe above (3/3 passed via `pnpm exec vitest run`, then deleted); full suite regression 22 files / 154 tests passed at the same HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: '^dsh-codex\\.src\\.client\\.(ImagegenToolView\\.resultParts|ImagegenToolView\\.promptSummary|ImagegenToolView\\.GeneratedImage|loadImage)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 4, has_more false (`GeneratedImage` Function 97-159, `promptSummary` 80-86, `resultParts` 40-66, `loadImage` 77).

## Verdict
Adopt marker-scanning over concatenated text with explicit absent-field spreads, single-image selection, injectable promise-cached loaders, and degrade-to-raw presentation. Adapt the marker vocabulary (`output_path`/`output_error`), the JSON re-projection keys, and preview UX to your host. Omit direct filesystem access from the view — paths open through the host callback, bytes flow through the loader. Coverage: `src/client/ImagegenToolView.tsx` is `no_recorded_issue` + `metadata_match`; no dedicated spec exists (transient probe evidence recorded above).
