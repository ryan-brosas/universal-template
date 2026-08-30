<!-- capsule-v2 -->
# Agent progress accounting — why are input and output tokens tracked with opposite accumulation semantics?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How does a background agent compute live token/tool progress from assistant messages without double-counting?

## Latest-input, cumulative-output
**Path/Symbol:** `src/tasks/LocalAgentTask/LocalAgentTask.tsx:40-104`: `MAX_RECENT_ACTIVITIES=5`, `ProgressTracker`, `createProgressTracker`, `getTokenCountFromTracker`, `updateProgressFromMessage`, `getProgressUpdate`; summary-preserving merge :339-353 `updateAgentProgress`.
**Signature:** `updateProgressFromMessage(tracker: ProgressTracker, message: Message, resolveActivityDescription?: ActivityDescriptionResolver, tools?: Tools): void`.
**Data Shape:** tracker = `{ toolUseCount, latestInputTokens, cumulativeOutputTokens, recentActivities: ToolActivity[] }`; tokenCount reported = latest + cumulative. Per activity: precomputed `activityDescription` (from Tool.getActivityDescription at RECORDING time), `isSearch`/`isRead` classification via getToolSearchOrReadInfo.

### Decisive source
```ts
// Track input and output separately to avoid double-counting.
// input_tokens in Claude API is cumulative per turn (includes all previous context),
// so we keep the latest value. output_tokens is per-turn, so we sum those.
tracker.latestInputTokens =
  usage.input_tokens + (usage.cache_creation_input_tokens ?? 0)
    + (usage.cache_read_input_tokens ?? 0);
tracker.cumulativeOutputTokens += usage.output_tokens;
```

**Flow:** each assistant message → replace latestInputTokens (cache creation+read included), add output_tokens → per tool_use block increment count and push activity (omitting the internal SYNTHETIC_OUTPUT_TOOL_NAME) → shift-keep last 5. `updateAgentProgress` preserves an existing background-summary field so periodic summarization isn't clobbered by raw progress writes; `updateAgentSummary` emits SDK progress only when the consumer opted in (`getSdkAgentProgressSummariesEnabled()`), capturing stats inside the updater for use after it.
**Invariant:** Summing input_tokens across turns inflates counts quadratically (each turn re-reports full context); keeping ONLY the latest while summing outputs is the correct pairing for this API contract — porters applying uniform accumulation to both get wrong numbers immediately.
**Probe:** `grep -n "cumulative per turn" src/tasks/LocalAgentTask/LocalAgentTask.tsx` (:43-44) and `grep -n "SYNTHETIC_OUTPUT_TOOL_NAME" src/tasks/LocalAgentTask/LocalAgentTask.tsx` (:11 import, :80 check) and `grep -n "existingSummary ? {" src/tasks/LocalAgentTask/LocalAgentTask.tsx` (:347).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createProgressTracker updateProgressFromMessage", limit: 5 });
```

## Verdict
Adopt the asymmetric accumulation rule verbatim. Adapt usage-field names to your provider. Omit the activity-description resolver if you have no tool metadata surface.
