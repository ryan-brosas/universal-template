<!-- capsule-v2 -->
# Mid-run signal detection — when should a working agent be interrupted mid-turn?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What cheap, deterministic predicates distinguish "agent stuck" from "agent working" so steering can fire mid-run without a turn counter?

## detectMidRunSignals (`src/state/mid-run-signals.ts`)
**Path/Symbol:** `src/state/mid-run-signals.ts:detectMidRunSignals` (:31-39), `checkToolErrors` (:44-65), `checkFileReadLoop` (:80-103), `readLoopKey` (:69-78).
**Signature:** `detectMidRunSignals(messages: Message[]): MidRunSignal | null` where `MidRunSignal = {type:'tool_error'|'file_read_loop', detail?}`.
**Data Shape:** Input is the FULL message list; internally only `messages.slice(-SIGNAL_WINDOW=30)` is normalized+filtered. Constants: `CONSECUTIVE_ERROR_THRESHOLD=5`, `FILE_READ_LOOP_THRESHOLD=5`, `FILE_MUTATION_TOOLS={Edit,Write,edit,write,MultiEdit}`, `FILE_READ_TOOLS={Read,read,read_file,View}`.

### Decisive source
```ts
// tool-error streak: walk BACKWARD from the tail over at most 10 blocks
for (let i = blocks.length - 1; i >= Math.max(0, blocks.length - 10); i--) {
  const b = blocks[i];
  if (b.kind === 'tool_result' && b.isError) {
    consecutive++;
    if (consecutive >= CONSECUTIVE_ERROR_THRESHOLD) return {type:'tool_error', ...};
  } else if (b.kind === 'tool_call') continue;   // call between its results is expected
  else break;                                     // ANY success/user/assistant breaks streak
}
// read-loop key: offset/limit are LOAD-BEARING
if (offset != null || limit != null) return `${path}:${offset ?? ''}-${limit ?? ''}`;
return path;
```

**Flow:** `turn_end` fires after each LLM sub-turn → `detectMidRunSignals(messages)` → first signal by severity (tool_error checked BEFORE file_read_loop) → analyze → steer only if confidence ≥ 0.85 (`src/index.ts:216`). Read loop counts per KEY: same path with different offsets/limits are DIFFERENT keys (pagination ≠ loop); an Edit/Write of that path DELETES the counter (progress resets the loop).
**Invariant:** (1) Only the tail window matters — old errors never re-fire. (2) A single successful result anywhere in the backward scan kills the error-streak. (3) Mutation of a file resets ITS read counter but not others'. (4) The mid-run steer gate is stricter than settled steers: confidence ≥ 0.85 required here; the settled path has no threshold. (5) Signals are computed fresh each turn — stateless.
**Probe:** `tests/state.test.ts` — `detects five consecutive tool errors` (:330), `does not trigger on four consecutive tool errors` (:314), `does not trigger when a successful result breaks the error streak` (:349), `resets read loop counter when file is edited` (:395), `does not trigger file read loop when reading same file with different offsets` (:414), `prioritizes consecutive tool_error over file_read_loop` (:458).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "detectMidRunSignals FILE_READ_LOOP_THRESHOLD consecutive tool errors", limit: 8 });
```

## Verdict
Adopt both predicates + thresholds as the minimal stuck-detector pair. Adapt tool-name sets to your host's tool vocabulary (case variants matter — sets carry both). Omit pi's Message shape; any block stream with isError/name/args works.
