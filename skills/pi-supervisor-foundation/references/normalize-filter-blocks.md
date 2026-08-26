<!-- capsule-v2 -->
# Normalize & filter blocks — message→block normalization, sanitization, thinking/noise/XML-wrapper stripping

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What is the canonical intermediate representation between raw host messages and every extractor, and which content must never reach the LLM context?

## FlatMap to NormalizedBlocks
**Path/Symbol:** `src/compaction/normalize.ts:6-73` (`normalizeOne`/`normalize`); noise `src/compaction/filter-noise.ts:31-47`; sanitize `src/compaction/sanitize.ts:4-5`; types `src/compaction/types.ts`.
**Signature:** `normalize(messages: Message[]): NormalizedBlock[]`; `filterNoise(blocks): NormalizedBlock[]`.
**Data Shape:** Block kinds: `user | assistant | thinking | tool_call{name,args} | tool_result{name,text,isError} | bash{command,output,exitCode}`; every block keeps `sourceIndex` (message ordinal) for provenance refs.

### Decisive source
```ts
const ANSI_RE = /\x1b\[[0-9;]*[A-Za-z]/g;
const CTRL_RE = /[\x00-\x08\x0b\x0c\x0e-\x1f]/g;
export const sanitize = (text: string): string =>
  text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(ANSI_RE, '').replace(CTRL_RE, '');
```
Filter rules (filter-noise.ts): ALL thinking blocks dropped (:34); NOISE_TOOLS (TodoWrite/TodoRead/ToolSearch/WebSearch/AskUser/ExitSpecMode/GenerateDroid) dropped as both calls AND results; user text stripped of XML wrappers (`system-reminder|ide_opened_file|command-message|context-window-usage`) and dropped when nothing remains or it matches NOISE_STRINGS (`Continue from where you left off.` etc.). Assistant bashExecution messages become `bash` blocks carrying exitCode — later reused by the outstanding-context extractor.

**Flow:** messages → per-message flatMap (user images become `[image: mime]` markers; assistant parts split into text/thinking/tool_call blocks) → sanitize → filter → extractors.
**Invariant:** Sanitize runs at NORMALIZE time so every downstream consumer sees clean text exactly once. Thinking is dropped twice by accident-proofing (filter arm + brief switch case) — a porter keeping either one is still safe. Empty user text still yields an empty user block rather than vanishing (normalize :18) — filter removes it later if truly empty.
**Probe:** `grep -c "XML_WRAPPER_RE" src/compaction/filter-noise.ts` → 3; `grep -c "NOISE_TOOLS.has" src/compaction/filter-noise.ts` → 2. Direct tests: `tests/full-fidelity-snapshot.test.ts:88/:107/:117/:129` ("strips thinking blocks…", "removes thinking blocks", "removes noise tool calls (TodoWrite, etc.)", "removes XML wrapper noise from user messages").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "filterNoise|normalize|sanitize|clipSentence", limit: 10 });
```

## Verdict
Adopt the normalize→filter pipeline as the single trust boundary for LLM-facing context. Adapt NOISE_TOOLS/XML wrapper tag names to your host's prompt-injection surface. Omit the ANSI stripper only if your host never embeds terminal output — otherwise control characters will leak into prompts.
