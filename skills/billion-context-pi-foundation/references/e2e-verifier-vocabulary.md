<!-- capsule-v2 -->
# State-verifier assertion vocabulary — what can you assert about a finished agent run from its PERSISTED state alone?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How does a porter write post-run assertions against agent state files (blocks, nudges, coverage, tool usage) without instrumenting the agent itself?

## CompressionState assertions + covered-id union + observation-derived limits + session-log scan
**Path/Symbol:** `scripts/e2e/verify.mjs`: state-shape readers (:65-83), child-state scan (:86-99), observation derivations (:101-104), assertion vocabulary (:129-183), exit protocol (:185-190). Usage: `node verify.mjs <state-file> <scenario-file> [acp-dir]` with `OBSERVATIONS` env.
**Signature:** scenario `verify` block keys: blockCount / minBlockCount / maxBlockCount / activeBlockCount / min-maxCompressedCount / nudgeBaselineSet / tier2BaselineSet / summaryContains / childBlockCount / maxCompressCallsVisible / lastRequestCompressCalls / min-maxNudgeCount / compressionCount / toolInvoked.
**Data Shape:** persisted CompressionState: `state.blocks[]` (`blockId, active, tier, summary, directMessageIds, effectiveMessageIds, compressedTokens...`), `state.nudge` (`lastPerMessageNudgeTokens`, `lastShownByTier`), `state.stats` (`tokensCompressed`, `compressionCount`), `state.messageRefs` ({byRaw, byRef}); observations rows as produced by the fake LLM server.

### Decisive source
```ts
// :76-83 — 'compressed' means COVERED by an active block, i.e. the union of
// effectiveMessageIds over blocks whose active !== false (not block count!):
function coveredMessageIds() {
  const ids = new Set();
  for (const b of activeBlocks) for (const id of b.effectiveMessageIds || []) ids.add(id);
  return ids;
}

// :171-180 — toolInvoked scans the sibling SESSION LOG: the state file is the
// session log path + '.acp.json', so slicing 9 chars recovers '<ts>_<uuid>.jsonl'.
const sessionLog = statePath.endsWith(".acp.json") ? statePath.slice(0, -9) : statePath;
invoked = nameRe.test(raw) || toolNameRe.test(raw);   // "name":X or "toolName":X
```

**Flow:** expectations come from the scenario's `verify` object; every key is optional and absent keys assert nothing (`check` skips undefined expectations). Structural counts read the state file directly; compressed-count bounds use the covered-id union, NOT the number of blocks; nudge assertions translate to baseline arithmetic (`nudgeBaselineSet` = `lastPerMessageNudgeTokens != null && > 0`; tier-2 = `lastShownByTier[2] != null`). Behavioral limits derive from the fake server's observations filtered to NON-auxiliary parent requests: max/last `compressCallCount`, and nudge-detection counts. Child-agent coverage passes an optional directory: every sibling `.acp.json` except the parent's state file contributes its blocks to `childBlockCount`. Tool usage is proven by regex-scanning the sibling session log for either JSON key spelling.
**Invariant:** (1) assertions must hold against the PERSISTED state file — the same bytes a resumed session would load — never against in-memory harness views. (2) Covered != compressed-count-of-blocks; only active-block effective ids count. (3) Observation-derived assertions exclude auxiliary host traffic or they flake. (4) Missing evidence files degrade to skip-or-fail explicitly (unreadable state exits 1; absent observations yields empty list), never to silent pass.
**Probe:** executed as part of `npm run e2e -- 01-basic` this pass (verifier invoked by the runner with state/scenario/sessionDir/OBSERVATIONS); standalone static probe: node --check plus key-grep of the vocabulary above. Result recorded honestly in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "verify assertions blocks effectiveMessageIds nudge observations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: assert-on-persisted-state discipline, active-block covered-id union as the definition of 'compressed', non-auxiliary observation filtering, sibling-file child-state aggregation, and dual-key session-log tool detection when building any post-mortem verifier for agent runs. Adapt the state schema and log format to your platform. Omit the specific assertion key names (they mirror this repo's scenario fixtures).