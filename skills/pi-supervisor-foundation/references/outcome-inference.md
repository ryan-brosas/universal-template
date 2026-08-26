<!-- capsule-v2 -->
# Outcome inference — goal extraction from a fresh compaction summary with quote-strip and length-cap normalization

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you auto-infer a supervision goal from an existing conversation without polluting it with preamble or markdown?

## Dedicated system prompt + strict normalization
**Path/Symbol:** `src/core/inference.ts:14-28` (INFER_OUTCOME_SYSTEM_PROMPT), :34-77 (`inferOutcome`).
**Signature:** `inferOutcome(ctx, provider, modelId, signal?): Promise<string | null>`.
**Data Shape:** Returns null on: zero messages, empty formatted context, session start failure, null prompt result, any throw. Success path normalizes then slices to **200 chars**.

### Decisive source
```ts
    const result = await session.prompt(userPrompt, signal);
    session.dispose();
    if (!result) return null;
    return result
      .replace(/^["']|["']$/g, '')   // strip wrapping quotes the model added anyway
      .replace(/\n/g, ' ')           // single line — it becomes a UI goal string
      .trim()
      .slice(0, 200);
  } catch { return null; }
```
The dedicated system prompt demands: specific+measurable, action-oriented, concise (1–2 sentences, ideally under 100 chars), focused on core intent, "Respond with ONLY the outcome statement. No quotes, no markdown, no explanations." The user prompt feeds the SAME compaction pipeline output (`buildCompactionSummary` + `formatForSupervisor`) used for steering decisions.

**Flow:** /supervise with no args → hasUserMessages gate → infer via disposable one-shot SupervisorSession → normalize → state.start(inferred) → kickstart follow-up if idle.
**Invariant:** Inference uses its own THROWAWAY session (disposed immediately) rather than the reusable analysis session — different system prompt would otherwise poison the reuse key. Quote-stripping exists because models add quotes despite instructions; the slice(0,200) bounds what lands in widget lines and prompts regardless.
**Probe:** `grep -cF 'slice(0, 200)' src/core/inference.ts` → 1; `grep -cF 'replace(/\n/g' src/core/inference.ts` → 1. Direct tests: `tests/engine.test.ts:438-509+` describe('inferOutcome') — "returns null when sessionManager has no branch entries", "returns null when model not found in registry", "returns null when session fails to start", "extracts outcome successfully".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "inferOutcome|buildUserPrompt|getReframeGuidance", limit: 10 });
```

## Verdict
Adopt throwaway-session inference with aggressive output normalization for any auto-goal feature. Adapt the good-outcome examples to your domain. Omit nothing on the null arms — inference failure must degrade to asking the user for an explicit goal, never to a garbage goal string.
