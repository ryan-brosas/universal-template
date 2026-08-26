<!-- capsule-v2 -->
# Message projection normalizer — which session entries become LLM messages, and what must be dropped to keep providers happy?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** How do heterogeneous host session entries map into clean CoreMessages without triggering provider 400s?

## Role ladder + thinking-only drop + custom_message passthrough + safe stringify
**Path/Symbol:** `src/messages.ts`: `entriesToCoreMessages` (:18-36), `projectMessage` (:38-86), `fallbackText` (:88-95), `extractText` (:103-114).
**Signature:** `entriesToCoreMessages(entries: SessionEntry[]) -> CoreMessage[]`; roles projected: user → user, toolResult → tool, assistant → assistant/tool-call, everything else → user text or [].
**Data Shape:** multi-tool-call assistant turns split into one CoreMessage per call with id `<entryId>#<callId>`; single-call turns merge text + args.

### Decisive source
```ts
// messages.ts:77-79 — the drop that prevents provider 400s:
// "Drop thinking-only turns: empty assistant text makes OpenAI-compatible
//  providers (e.g. GLM) return 400 (no body), which Pi misreads as overflow."
if (!text.trim()) return [];
```

```ts
// :22-29 — non-message entries still in LLM context get a user projection:
// custom_message participates in LLM context per Pi native semantics —
// project it as a user message (empty content dropped).
```

**Flow:** iterate entries → skip non-message types except `custom_message` (→ user text) → per role: user/toolResult project directly; assistant first extracts ALL toolCall blocks (splitting when >1, joining text+args when exactly 1), else emits text and DROPS whitespace-only turns. Unmatched roles (omp's bashExecution etc.) fall back to `$ <command>` + output + summary joined as user text. All stringification guarded (`safeStringify`), all tag stripping via the anchored REF_TAG.
**Invariant:** (1) an assistant message with empty/whitespace text must NEVER reach OpenAI-compatible providers — it 400s and the host misreads the failure as context overflow. (2) Projections are lossless on ids so the reverse mapping (coreOutToAgentMessages) can restore originals. (3) Content extraction tolerates string OR block-array forms everywhere.
**Probe:** `tests/messages.test.ts:60-251`: role projections (:60), thinking-only drop (:91), thinking+text keeps text (:106), whitespace-only drop (:118), custom_message string/array/empty/non-text (:139-190), full round-trip (:199), compaction/model_change skipped (:240), omp execution roles preserved as user text (:251).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "entriesToCoreMessages projectMessage fallbackText", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the projection ladder verbatim — each rule corresponds to an observed provider/host failure mode. Adopt the thinking-only drop for ANY OpenAI-compatible target. Adapt role names to your host vocabulary. Omit omp execution-role handling unless porting to that host.
