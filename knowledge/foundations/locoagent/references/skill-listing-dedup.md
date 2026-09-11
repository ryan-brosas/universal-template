<!-- capsule-v2 -->
# Skill listing dedup — per-agent sent-sets, resume suppression, and the bundled+MCP fallback ladder?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** announcing available skills exactly once per agent without re-injecting across resumes.

## getSkillListingAttachments
**Path/Symbol:** `src/utils/attachments.ts:getSkillListingAttachments` (:2661-2751), `sentSkillNames` map (:2603-2607), `resetSentSkillNames` (:2612-2615), `suppressNextSkillListing` (:2633-2636), `filterToBundledAndMcp` (:2651-2659), `FILTERED_LISTING_MAX = 30` (:2641).
**Signature:** `(toolUseContext) → Promise<Attachment[]>`; module state `Map<agentId /* '' = main */, Set<skillName>>` plus boolean `suppressNext`.
**Data Shape:** emits `skill_listing { content, skillCount, isInitial }`; formatting budgeted via `formatCommandsWithinBudget(newSkills, contextWindowTokens)`.

### Decisive source
```ts
// Track which skills have been sent to avoid re-sending. Keyed by agentId
// (empty string = main thread) so subagents get their own turn-0 listing —
// without per-agent scoping, the main thread populating this Set would cause
// every subagent's filterToBundledAndMcp result to dedup to empty.
const sentSkillNames = new Map<string, Set<string>>()
// suppressNextSkillListing(): Called by conversationRecovery on --resume when
// a skill_listing attachment already exists in the transcript.
// `sentSkillNames` is module-scope — process-local. Each `claude -p` spawn
// starts with an empty Map, so without this every resume re-injects the
// full ~600-token listing ... Shows up on every --resume; particularly
// loud for daemons that respawn frequently.
```

**Flow:** skip when NODE_ENV=test / no Skill tool in pool → gather local + MCP commands (uniqBy name; MCP-first presence decides union) → skill-search active? filter to bundled+MCP, falling back to bundled-only if > 30 (protects MCP-heavy users while keeping turn-0 guarantee) → resume path: mark ALL current as sent, return [] → diff vs sent-set; empty diff → [] → else emit with `isInitial = sent.size === 0` then mark sent. Reset ONLY on genuine skill-set change (plugin reload), never on compact ("post-compact re-injection costs ~4K tokens/event for marginal benefit").
**Invariant:** dedup state is per-agentId or subagents inherit the main thread's emptiness and get NOTHING; cross-process duplication needs a transcript-derived suppression signal because module maps die with the process; listing changes should be announced as DELTAS (reset marks everything re-sendable) not full re-lists after compaction.
**Probe:** no upstream test (coverage caveat); comments pinned verbatim :2603-2606 and :2617-2631. Deterministic probe: `grep -n "suppressNext\|FILTERED_LISTING_MAX" src/utils/attachments.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "skill_listing sentSkillNames suppressNext filterToBundledAndMcp", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-agent sent-sets + explicit resume suppression + tiered fallback filtering; adapt sources/thresholds; omit DCE require tricks. Porting trap: a single global sent-set starves every subagent of the listing; ignoring --resume spawns ~600 tokens of duplicate listing on every daemon respawn.
