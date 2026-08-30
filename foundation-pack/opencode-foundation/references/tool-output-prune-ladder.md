<!-- capsule-v2 -->
# Tool-output prune ladder — how does opencode reclaim context from old tool results without losing the transcript?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How are old completed tool outputs erased while protecting recent history and special tools?

## Backward-walk protection window
**Path/Symbol:** `packages/opencode/src/session/compaction.ts` (layer `prune` :273–317; constants :28-33).
**Signature:** `prune({sessionID}) → Effect<void>` — config-gated, no-op unless `cfg.compaction.prune === true`.
**Data Shape:** Walks `SessionV1.WithParts` backwards; mutates only `part.state.time.compacted = Date.now()` on qualifying tool parts — output text is NEVER rewritten or deleted in storage; serialization renders compacted parts as `[Old tool result content cleared]` (:76-78).

### Decisive source
```ts
// compaction.ts:288-305
loop: for (let msgIndex = msgs.length - 1; msgIndex >= 0; msgIndex--) {
  const msg = msgs[msgIndex]
  if (msg.info.role === "user") turns++
  if (turns < 2) continue                        // newest user turn is untouchable
  if (msg.info.role === "assistant" && msg.info.summary) break loop   // stop at prior compaction summary
  for (let partIndex = msg.parts.length - 1; partIndex >= 0; partIndex--) {
    const part = msg.parts[partIndex]
    if (part.type !== "tool") continue
    if (part.state.status !== "completed") continue
    if (PRUNE_PROTECTED_TOOLS.includes(part.tool)) continue      // ["skill"] :31
    if (part.state.time.compacted) break loop                    // already-pruned frontier ⇒ done
    const estimate = Token.estimate(part.state.output)
    total += estimate
    if (total <= PRUNE_PROTECT) continue         // protect newest 40k tokens of tool output
    pruned += estimate
    toPrune.push(part)
  }
}
// compaction.ts:308-316 — write only when the harvest clears the minimum-worth bar
if (pruned > PRUNE_MINIMUM) {                     // 20_000 :28
  for (const part of toPrune) {
    if (part.state.status === "completed") {
      part.state.time.compacted = Date.now()
      yield* session.updatePart(part)
    }
  }
}
```

**Flow:** Config gate first (`compaction?.prune`, :275); session-missing NotFoundError degrades to silent no-op (:278-281). The walk protects: (1) everything before the SECOND-newest user turn (`turns < 2` counts user messages as it walks backward), (2) anything at/behind a prior assistant `summary` message, (3) the newest `PRUNE_PROTECT=40_000` estimated tokens of tool output, (4) `skill` tool outputs unconditionally. First already-compacted tool part STOPS the loop (`break loop` :298) — a second prune run never rescans old ground.
**Invariant:** Prune is a MARKING operation, not deletion: `time.compacted` timestamps drive both serialization ("[Old tool result content cleared]") and future walks. The two-threshold design matters — PRUNE_PROTECT (40k) decides WHICH parts qualify; PRUNE_MINIMUM (20k) decides whether ANYTHING is written. A porter who collapses them into one threshold will stamp tiny sessions pointlessly or skip worthwhile harvests.
**Probe:** `packages/opencode/test/session/compaction.test.ts:626` `describe("session.compaction.prune")` — ":628-ish compacts old completed tool output" asserts `part.state.time.compacted` becomes a number after `compact.prune(...)` under `{config:{compaction:{prune:true}}}` (:700-722); ":725 skips protected skill tool output" keeps a `tool:"skill"` part's state intact (:773, :801).
```bash
grep -n 'PRUNE_PROTECT\|PRUNE_MINIMUM\|PRUNE_PROTECTED_TOOLS' packages/opencode/src/session/compaction.ts
```
expect exactly :28,:29,:31,:297,:301,:308.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", name_pattern: "PRUNE_PROTECT", limit: 5 });
// resolves opencode.packages.opencode.src.session.compaction.PRUNE_MINIMUM / PRUNE_PROTECT /
// PRUNE_PROTECTED_TOOLS constants (compaction.ts:28-31); the Effect-fn `prune` closure itself is NOT
// a graph node (known Effect-gen class) — the constants are the stable anchor.
```

## Verdict
Adopt the marking-not-deleting prune with dual thresholds + protected-tool list; adapt token estimation and storage update calls; omit SessionV1 part schema specifics.
