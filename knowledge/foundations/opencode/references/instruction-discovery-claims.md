<!-- capsule-v2 -->
# Instruction file discovery — how do AGENTS.md/CLAUDE.md get found, deduped, and attached once per message?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** What is the precedence ladder for instruction files, and which three mechanisms prevent duplicate attachment?

## First-match-wins discovery + claims ledger
**Path/Symbol:** `packages/opencode/src/session/instruction.ts` (whole file, 237L; `systemPaths` :110–153; `resolve` :179–221; claims state :70–77; `extract` :17–32).
**Signature:** `system(): Effect<string[]>`; `resolve(messages, filepath, messageID): Effect<{filepath, content}[], FSUtil.Error>`.
**Data Shape:** Global files: `~/.config/opencode/AGENTS.md` then `~/.claude/CLAUDE.md` (first EXISTS wins — break). Project files: first of [AGENTS.md, CLAUDE.md, CONTEXT.md(deprecated)] with any findUp match from directory→worktree. `config.instructions`: http(s) URLs deferred to fetch lane; `~/` expands to home; absolute paths glob their dirname basename; relative paths globUp from worktree. Dedup trio: (1) `paths` is a Set, (2) `sys.has(found)` skips already-system files, (3) per-messageID `claims: Map<MessageID, Set<string>>`.

### Decisive source
```ts
// instruction.ts:122-131 — ONE ancestor level contributes project instructions, not all
// The first project-level match wins so we don't stack AGENTS.md/CLAUDE.md from every ancestor.
for (const file of instructionFiles) {
  const matches = yield* fs.findUp(file, ctx.directory, ctx.worktree).pipe(Effect.catch(() => Effect.succeed([])))
  if (matches.length > 0) { matches.forEach((item) => paths.add(path.resolve(item))); break }
}
// instruction.ts:194-217 — upward walk from the READ file, claim-once per assistant message
while (current.startsWith(root) && current !== root) {
  const found = yield* find(current)
  if (!found || found === target || sys.has(found) || already.has(found)) { current = path.dirname(current); continue }
  ...set.add(found); results.push({ filepath: found, content: `Instructions from: ${found}\n${content}` })
}
```

**Flow:** system() assembles `[Instructions from: <path>\n<body>]` blocks: files read at concurrency 8, remote URLs fetched with a 5000ms timeout and empty-string failure swallow → prompt.ts orders system `[...env, ...instructions, ...(mcpInstructions), ...(skills)]`. resolve() runs when the Read tool loads a file: walk UP from its directory collecting nearby instruction files not already in system/history (`extract` scans completed read-tool parts' `metadata.loaded` arrays, skipping compacted) nor claimed for this message.
**Invariant:** Exactly one project-level instruction file per hierarchy — stacking every ancestor's AGENTS.md would multiply context on monorepo roots. Claims are keyed by ASSISTANT message id and cleared via `instruction.clear(messageID)` finalizers wired into createUserMessage AND the loop outcome block (`Effect.ensuring`) — leaking claims would silently suppress instructions on later turns sharing the id.
**Probe:** `packages/opencode/test/session/instruction.test.ts` (writeFiles/provideInstruction fixtures around :35–73); MCP-instruction ordering pinned at `prompt.test.ts:557` ("loop includes MCP instructions in model system context" asserts `<server name=\"guide-server\">` reaches request body).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "instruction files AGENTS findUp claims", limit: 8 });
```

## Verdict
Adopt first-match-wins ladders, the claims-ledger once-per-message attach, and extract-from-tool-history dedup; adapt glob/findUp utilities; omit CLAUDE.md compat flag wiring details.
