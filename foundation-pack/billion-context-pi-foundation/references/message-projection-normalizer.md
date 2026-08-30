<!-- capsule-v2 -->
# Message projection normalizer — which session entries become LLM messages, and what must be dropped to keep providers happy?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How do heterogeneous host session entries map into clean CoreMessages without triggering provider 400s?

## Role ladder + thinking-only drop + custom_message passthrough + safe stringify
**Path/Symbol:** `src/messages.ts`: `entriesToCoreMessages` (:21-39), `projectMessage` (:41-89), `fallbackText` (:91-98), `extractText` (:107-116).
**Signature:** `entriesToCoreMessages(entries: SessionEntry[]) -> CoreMessage[]`; roles projected: user → user, toolResult → tool, assistant → assistant/tool-call, everything else → user text or [].
**Data Shape:** multi-tool-call assistant turns split into one CoreMessage per call with id `<entryId>#<callId>`; single-call turns merge text + args.

### Decisive source
```ts
// messages.ts:80-82 — the drop that prevents provider 400s:
// "Drop thinking-only turns: empty assistant text makes OpenAI-compatible
//  providers (e.g. GLM) return 400 (no body), which Pi misreads as overflow."
if (!text.trim()) return [];
```

```ts
// :24-32 — non-message entries still in LLM context get a user projection:
// "custom_message participates in LLM context per Pi native semantics
//  (session-manager.d.ts) — project it as a user message."
if (entry.type === "custom_message") {
  const text = extractText(entry.content);
  if (text.length > 0) out.push({ id: entry.id, role: "user", contentType: "text", text });
}
```

**Flow:** iterate entries → skip non-message types except `custom_message` (→ user text) → per role: user/toolResult project directly; assistant first extracts ALL toolCall blocks (splitting when >1, joining text+args when exactly 1), else emits text and DROPS whitespace-only turns. Unmatched roles (omp's bashExecution etc.) fall back to `$ <command>` + output + summary joined as user text. All stringification guarded (`safeStringify`), all tag stripping via the anchored REF_TAG.
**Invariant:** (1) an assistant message with empty/whitespace text must NEVER reach OpenAI-compatible providers — it 400s and the host misreads the failure as context overflow. (2) Projections are lossless on ids so the reverse mapping (coreOutToAgentMessages) can restore originals. (3) Content extraction tolerates string OR block-array forms everywhere.
**Probe:** `tests/messages.test.ts:60-251`: role projections (:60), thinking-only drop (:91), thinking+text keeps text (:106), whitespace-only drop (:118), custom_message string/array/empty/non-text (:139-190), full round-trip (:199), compaction/model_change skipped (:240), omp execution roles preserved as user text (:251).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "entriesToCoreMessages projectMessage fallbackText", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the projection ladder verbatim — each rule corresponds to an observed provider/host failure mode. Adopt the thinking-only drop for ANY OpenAI-compatible target. Adapt role names to your host vocabulary. Omit omp execution-role handling unless porting to that host.
