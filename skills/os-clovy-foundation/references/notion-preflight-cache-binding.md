<!-- capsule-v2 -->
# Approval preflight cache binding — how does a "what will happen" preview stay bound to its exact tool call?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter adding show-before-approve guardrails must keep each preview attached to the right callId across concurrency, pauses, and abandoned runs.

## Input-guardrail preflight → cache → presentation binding
**Path/Symbol:** `agent-runtime/src/sdk-engine.ts` — guardrail registration in `createTool` (:253-271), cache field `notionPreflights` (:78), consumption + prune in `consumeStream` (:324-359).
**Signature:** guardrail `run({toolCall}) => {behavior:{type:"allow"}|{type:"rejectContent",message}}`; key `` `${runId}:${callId}` ``, value = host preflight result `JsonObject`.
**Data Shape:** Preflight result fields consumed: `title`, `description`, `command`, `preview`, `digest` (all via `stringValue` — empty/absent falls back to defaults). They land on the interruption as `approvalPresentation` and `approvalBinding{digest}`.

### Decisive source
```ts
// BEFORE pause: guardrail calls the host preflight tool, caches by run+call
const result = await this.invokeHostTool({ ..., name: "__clovy_notion_action_preflight",
  arguments: { toolName: descriptor.name, arguments: argumentsJson }, callId });
if (isRecord(result)) this.notionPreflights.set(`${runId}:${callId}`, result as JsonObject);
return { behavior: { type: "allow" } };
//   catch → { behavior: { type: "rejectContent", message: errorMessage(error) } }

// AT stream settle: consume into the mapped approval, prune the rest of THIS run
const key = `${runId}:${mapped.id}`;
activeKeys.add(key);
const preflight = this.notionPreflights.get(key);
this.notionPreflights.delete(key);                 // consume-once
if (mapped.kind !== "approval" || !preflight) return mapped;
return { ...mapped,
  approvalPresentation: { title: ... ?? "Approval required",
    description: ... ?? "Review this Notion action.",
    command: ... ?? mapped.toolName, preview: ... ?? "" },
  approvalBinding: { digest: stringValue(preflight.digest) ?? "" } };
for (const key of this.notionPreflights.keys())
  if (key.startsWith(`${runId}:`) && !activeKeys.has(key)) this.notionPreflights.delete(key);
```

**Flow:** tool with `notionAction` set gets an SDK input guardrail → preflight executes against the host before the tool may run; failure REJECTS the content (model sees why) instead of allowing a blind call → stream pauses on approval → at settle, each interruption consumes exactly its `${runId}:${callId}` entry into `approvalPresentation`+`approvalBinding.digest` → leftover same-run keys (tool retracted mid-stream, parallel calls that never paused) are pruned; other runs' keys are untouched.
**Invariant:** Binding is exact per callId even under concurrent tool calls (test drives slow+fast calls with distinct digests and asserts each approval keeps its own); entries are consume-once (deleted on read), so a stale preview can never attach to a later resume; pruning is scoped to the current runId prefix — one run's GC never destroys another's cached preflights.
**Probe:** `agent-runtime/test/sdk-tool-loop.test.ts` — "keeps concurrent Notion preflights bound to their original tool call ids" (:1284+, slow call delayed 25ms so completions interleave; digests asserted per callId) and "preflights a Notion action before interruption and again before approved execution" (:1142-1282). Suite runner-blocked at pin; ranges read directly.

## Get live surrounding code
**Retrieve:** executed at pin (createTool snippet carries the guardrail block; family search):
```
search_graph({ project:"os-clovy", query:"reserved host tool invoke callback execute", file_pattern:"agent-runtime/*" })
→ src.sdk-engine.OpenAIAgentsEngine.createTool Method sdk-engine.ts 241-309  (guardrail inline :253-271)
```
(Cache touch points :78/:274/:341-342/:357-358 are property-level state — located by direct grep after the graph selected createTool/consumeStream.)

## Verdict
Adopt the three-point contract: preflight-before-pause keyed by run+call, consume-once presentation binding at interruption mapping, and run-scoped prune. Adapt the preflight result schema (title/description/command/preview/digest) to your approval UI. Omit the Notion-specific tool names; keep the `rejectContent` failure posture — a preflight that cannot render must not silently allow the action.
