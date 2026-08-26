<!-- capsule-v2 -->
# System-prompt family selection — how does the model id pick the base prompt, and what order do system blocks stack?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** Which substring ladder maps a model to its base prompt file, and what is the canonical system assembly order?

## Substring-routed prompt variants
**Path/Symbol:** `packages/opencode/src/session/system.ts` (`provider`, lines 27–49; Service :59–137).
**Signature:** `provider(model: Provider.Model): string[]` (pure); service methods `environment(model)`, `skills(agent)`, `mcp(agent, permission?)`.
**Data Shape:** Ladder on `model.api.id`: "muse" → META template with {{MODEL_NAME}} = Muse Glimmer/Spark; "gpt-4"|"o1"|"o3" → BEAST; "gpt"+"codex" → CODEX else GPT; "gemini-" → GEMINI; "claude" → ANTHROPIC; "trinity" → TRINITY; "kimi" in id OR providerID ∈ {kimi-for-coding, moonshotai, moonshotai-cn} → KIMI; default → DEFAULT. Each variant is a whole .txt imported at build time from `session/prompt/*.txt`.
**Decisive source:**
```ts
// system.ts:34-41 — order matters: codex check INSIDE gpt branch, beast BEFORE gpt
if (model.api.id.includes("gpt-4") || model.api.id.includes("o1") || model.api.id.includes("o3"))
  return [PROMPT_BEAST]
if (model.api.id.includes("gpt")) {
  if (model.api.id.includes("codex")) return [PROMPT_CODEX]
  return [PROMPT_GPT]
}
...
// prompt.ts:1264-1271 — canonical stack assembled by the loop
const system = [...env, ...instructions, ...(mcpInstructions ? [mcpInstructions] : []), ...(skills ? [skills] : [])]
if (format.type === "json_schema") system.push(STRUCTURED_OUTPUT_SYSTEM_PROMPT)
```

**Flow:** environment() renders identity line ("You are powered by the model named X. The exact model ID is provider/api-id"), `<env>` block (cwd/worktree/git-ness/platform/date — date via `toDateString` so it's stable within a day), and an optional alphabetized `<available_references>` XML block only when references carry descriptions. skills() skips entirely when agent permission disables "skill", renders verbose list (comment: agents ingest verbose-in-system + terse-in-tool better than inverse). mcp() merges permission rulesets and keeps only servers whose tools aren't fully disabled, emitting `<mcp_instructions><server name="…">…</server></mcp_instructions>`.
**Invariant:** The base-prompt choice is a PURE function of model id/provider — no config override — so a porter adding a vendor must extend the ladder or their users silently get PROMPT_DEFAULT. The env block goes FIRST because later blocks assume location context; structured-output directive is LAST so it reads as the operative final instruction.
**Probe:** no direct unit test for `provider()` mapping (pure data routing — source-pinned); assembly order pinned behaviorally by `prompt.test.ts:557` MCP-instructions-in-body assertion; skills/mcp gating exercised through tool-permission suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SystemPrompt.mcp skills environment", limit: 8 });
```

## Verdict
Adopt pure-substring routing + fixed block order (env→instructions→mcp→skills→[structured-output]); adapt vendor substrings to host model catalog; omit .txt bodies.
