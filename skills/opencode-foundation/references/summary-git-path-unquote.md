<!-- capsule-v2 -->
# Git-path unquoting and step-snapshot diffing — how does opencode attribute file diffs to a turn when git quotes weird filenames?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How are per-turn file diffs computed from snapshots, and how are git's quoted/octal-escaped paths decoded back to real filenames?

## Snapshot-pair diff extraction
**Path/Symbol:** `packages/opencode/src/session/summary.ts` (`computeDiff` :82–100; `summarize` :102–127; `diff` :129–142).
**Signature:** `computeDiff({messages}) → FileDiff[]` / `summarize({sessionID, messageID}) → void` / `diff({sessionID, messageID?}) → FileDiff[]`.
**Data Shape:** Diffs ride on the USER message's `info.summary.diffs` array. Snapshot refs live on stream bookkeeping parts: `step-start` parts carry the BEFORE snapshot, `step-finish` parts carry the AFTER snapshot.

### Decisive source
```ts
// summary.ts:83-99 — first step-start snapshot = from; LAST step-finish snapshot = to
let from: string | undefined
let to: string | undefined
for (const item of input.messages) {
  if (!from) {
    for (const part of item.parts) {
      if (part.type === "step-start" && part.snapshot) { from = part.snapshot; break }
    }
  }
  for (const part of item.parts) {
    if (part.type === "step-finish" && part.snapshot) to = part.snapshot   // keeps overwriting ⇒ last wins
  }
}
if (from && to) return yield* snapshot.diffFull(from, to)
return []
```

**Flow:** `summarize` first zeroes the session summary and publishes an empty Diff event (optimistic UI reset), bails entirely when `config.snapshot === false` (:115), then scopes messages to the target user message plus assistant children with matching parentID, computes the diff pair, and stores it on `target.info.summary.diffs`. The read-side `diff` maps stored FileDiffs through `unquoteGitPath` before returning.
**Invariant:** Both endpoints must exist or the diff is silently empty — a turn whose step-start lacked a snapshot (e.g. pre-snapshot history) yields [] rather than guessing from the worktree. The last-wins overwrite for `to` is deliberate: multi-step turns diff against their FINAL state.
**Probe:** direct source pin:
```bash
grep -n 'step-start\|step-finish\|diffFull' packages/opencode/src/session/summary.ts
```
expect :88,:89,:95,:98 exactly.

## Git quoted-path decoding
**Path/Symbol:** same file, `unquoteGitPath` :10–64.
**Signature:** `(input: string) => string` — identity unless wrapped in literal double quotes.
**Data Shape:** Handles git's two quoting layers: C-style escapes (`\n \r \t \b \f \v \\ \"`) and three-digit-max OCTAL byte escapes (`\303\251` for é), accumulating raw char codes into a Buffer.

### Decisive source
```ts
// summary.ts:29-40 — octal runs consume 1-3 digits, NOT always exactly 3
if (next >= "0" && next <= "7") {
  const chunk = body.slice(i + 1, i + 4)
  const match = chunk.match(/^[0-7]{1,3}/)
  if (!match) { bytes.push(next.charCodeAt(0)); i++; continue }   // lone backslash-digit ⇒ literal
  bytes.push(parseInt(match[0], 8))
  i += match[0].length                                            // advance by digits consumed
  continue
}
// summary.ts:63 — decode via byte buffer so multi-byte UTF-8 survives octal splitting
return Buffer.from(bytes).toString()
```

**Flow:** Git emits `"quoted"` paths only when the filename contains special characters (config `core.quotePath` default true); without decoding, diff entries show `"\303\251.txt"` instead of `é.txt` and UI links break. Unknown escapes after `\` fall back to the literal next char; a trailing lone `\` pushes itself.
**Invariant:** Octal escapes must be consumed greedily up to THREE digits per run but the Buffer assembly must stay byte-level until the final `.toString()` — decoding each escape to its own string would split multibyte UTF-8 sequences mid-character.
**Probe:** direct source pin:
```bash
grep -c 'charCodeAt' packages/opencode/src/session/summary.ts
```
expect ≥6 (byte-accumulation loop).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", name_pattern: "unquoteGitPath", limit: 5 });
// resolves opencode.packages.opencode.src.session.summary.unquoteGitPath (summary.ts:10-64) and its
// app-side twin packages/app/src/context/file/path.ts; computeDiff resolves via
// name_pattern "computeDiff" onto the test suites (compaction.test.ts / processor-effect.test.ts).
```

## Verdict
Adopt step-start/step-finish snapshot pairing + byte-buffer git path unquoting verbatim; adapt Snapshot service to host VCS; omit SessionV1 part schemas.
