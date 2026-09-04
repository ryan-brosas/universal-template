<!-- capsule-v2 -->
# Actor context digest — how do you hand a watching actor a cheap, byte-stable summary of a host session?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How does an actor observe a host event and receive session context without ingesting the whole transcript?

## Actor context digest
**Path/Symbol:** `src/actors/context.ts:buildActorContext` (:170–182), `buildDigest` :111–128, `scanFiles` :88–109, `boundLines` :160–168.
**Signature:** `buildActorContext(branch: unknown[], tailCount: number, maxChars: number): {digest: {filesTouched, openErrors, lastError, lastUserRequest}, transcript: string[]}`.
**Data Shape:** digest filesTouched ≤30 sorted paths; openErrors counts error toolResults + non-zero bash exitCodes; transcript lines prefixed `user:` / `asst:` / `call: <tool> <argHint>` / `result <tool>:` (+` [ERR]`) / `bash: <cmd> -> <exit>`.

### Decisive source
```ts
const extractMessages = (branch: unknown[]): ActorMessage[] => {
  // wrapped pass first; only if it found wrapped entries do we trust that shape
  if (foundWrapped) return messages;
  for (const entry of branch) if (isMessage(entry)) messages.push(entry);
  return messages;
};
...
while ((match = PATH_RE.exec(hay)) !== null) {
    if (match[2]) seen.add(match[2]);
    if (seen.size >= cap * 3) break;   // over-harvest then sort+slice(0, cap)
}
```

**Flow:** host event fires → fabric-state calls buildActorContext with the live branch → digest built from ALL messages, transcript from the LAST tailCount messages oldest-first → char budget applied by dropping OLDEST lines until under maxChars (`out.shift()` loop) → both run through the payload redactor before mesh dispatch.
**Invariant:** Two envelope shapes supported but NEVER mixed — the `{type:"message", message}` wrapper is detected first and wins wholesale; bare-message fallback only when zero wrappers found. File scanning harvests up to cap×3 raw matches then takes the SORTED first cap (alphabetical, not recency — deterministic); regex is module-level with `/g` so `PATH_RE.lastIndex = 0` MUST be reset per message (stateful-exec trap); thinking blocks are skipped entirely; identical input produces byte-identical digests (cache-friendly, test-pinned).
**Probe:** `tests/actor-context.test.ts` ("produces a byte-stable digest for identical input (cache-friendly)"); grep -c 'caps the transcript to the tail count of messages' tests/actor-context.test.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "buildActorContext digest transcript actor branch", limit: 10 });
// buildActorContext Function src/actors/context.ts 170-182
```

## Verdict
Adopt the two-shape envelope detection and sorted-cap file harvesting for any observer that summarizes sessions; adapt line prefixes/arg-hint keys to your tool names; omit the bashExecution role if your host lacks it.
