<!-- capsule-v2 -->
# Ref-tag round-trip — how are mNNNNN refs injected for the LLM yet kept out of the persisted session?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** How do stable per-message references get shown to the model, stripped from storage, and re-attached after kernel processing — including assistant-echo prevention and body-mutation reconciliation?

## Tags live ONLY in the LLM-bound projection; the session log stays clean
**Path/Symbol:** `src/messages.ts`: `REF_TAG` (:16), `patchRefTag` (:219-266), `coreOutToAgentMessages` (:134-169).
**Signature:** `REF_TAG = /^(?:<acp\s[^>]*>m\d{5}<\/acp>|\[m\d{1,5}\])\s?\n?/`; `entriesToCoreMessages(entries) -> CoreMessage[]` strips it on the way IN; `coreOutToAgentMessages(coreOut, originalById)` re-injects it on the way OUT.
**Data Shape:** tag forms `<acp tokens="2.1K" type="bash">m00175</acp>` (new) or legacy `[m175]`; every message carries a stable entry id (`m00350`); split multi-tool-call turns get synthetic ids `<entryId>#<callId>`.

### Decisive source
```ts
// messages.ts:224-239 — two load-bearing rules in one function
// Skip tag injection for assistant messages — the model sees tags on its own
// previous responses and echoes them, causing visible tag fragments in the terminal.
if (base.role === "assistant") return original;
// Honor kernel body mutations (emergency truncation of large tool-results,
// future rewrites): if core.text's body differs from the original text,
// rebuild from the kernel body — otherwise truncation never reaches the model.
const coreBody = core.text ? core.text.slice(bodyStart) : "";
if (coreBody && trimEnd(coreBody) !== trimEnd(originalBody)) {
  return rebuildBodyFromCore(original, coreBody, tag);
}
```

**Flow:** session entries → CoreMessages with tags stripped (`extractText`) → kernel prunes/summarizes → `coreOutToAgentMessages` maps each surviving CoreMessage back: plain id → `patchRefTag` re-injects the tag into the LAST text block of the ORIGINAL message object; `<id>#<callId>` → first split message reconstructs a single AgentMessage filtered to SURVIVING call ids only (deduped via an `emittedSplit` Set so N split cores yield ONE restored message); ids starting `acp_summary_` are skipped (synthetic summaries never map back to originals).
**Invariant:** (1) assistant messages are NEVER tagged — models echo their own prior tags into visible terminal output; they must infer refs from adjacent tagged user/tool messages. (2) If the kernel mutated a message body (e.g. emergency truncation), rebuild from the KERNEL body, not the original — otherwise truncation silently never reaches the model. (3) Tag stripping is idempotent (regex anchored at start) so double-projection cannot stack tags. The status command states the doctrine: "tags injected to LLM only (deep copy), not persisted in session, not shown in terminal."
**Probe:** `tests/messages.test.ts:199` (custom_message full round-trip entriesTo → collectOriginals → coreOutTo preserves user role); `tests/integration.test.ts:72` (every outgoing message carries a ref).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "patchRefTag REF_TAG coreOutToAgentMessages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way invariant (LLM-only tags, assistant no-tag, kernel-body-wins). Adopt the `#callId` split-id + emittedSplit dedup if your host collapses multi-tool-call assistant turns. Adapt the tag vocabulary to your own namespace but keep refs 5-digit zero-padded and sort-stable. Omit omp-specific role names (`bashExecution`) unless porting to that host.
