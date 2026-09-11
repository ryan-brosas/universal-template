<!-- capsule-v2 -->
# Tool-result guardrails — how are bash timeouts defaulted and runaway tool outputs capped without losing the full text?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** Where must timeout injection and output capping hook in, and what does the cap notice need to contain so the model can recover the dropped bytes?

## Inject timeout at call time; cap UTF-8-safe at result time; always teach recovery
**Path/Symbol:** `src/tool-guardrails.ts`: `resolveBashTimeout` (:20-28), `capToolOutput` (:30-51), `keepHead` (:81-94), `wireToolGuardrails` (:112-147).
**Signature:** `capToolOutput(content, maxBytes, fullPath?) -> content | undefined`; `resolveBashTimeout(input, defaultTimeout) -> number | undefined`.
**Data Shape:** defaults: `DEFAULT_TOOL_BASH_TIMEOUT=60`, `DEFAULT_TOOL_OUTPUT_MAX_BYTES=200_000` (config.ts:45-46). Cap applies to TEXT parts only; non-text parts (images) pass through untouched.

### Decisive source
```ts
// keepHead :81-93 — byte cap with UTF-8 + line discipline:
// back off past continuation bytes ((b & 0xc0) !== 0x80) so a multibyte char
// is never split, THEN cut to the last newline when it sits in the second
// half of the budget — "keeps a complete last line (no mid-line cut)".
// buildCapNotice tells the model HOW to recover:
// bash: "Full output saved to: <fullOutputPath> — read it to see everything."
// other: "narrow the query or redirect output to a file and read the relevant slice."
```

**Flow:** on `tool_call` (bash only): if the model OMITTED `timeout`, inject the configured default — model-specified values pass through untouched (`input.timeout !== undefined → return undefined`); disabled (0/neg/NaN) means no injection. On `tool_result`: detect pi's own timeout text via regex `/Command timed out after (\d+) seconds/`, then append an actionable notice suggesting `timeout: min(2×secs, clamp [120..3600])`; separately cap oversized combined text and append `[ACP guardrail: output capped at X (~Y dropped) …]`.
**Invariant:** (1) user/model-explicit values always win over defaults. (2) Capping measures BYTES not chars and never splits a UTF-8 codepoint or a logical line. (3) A cap notice MUST name the recovery path (full-output file for bash; query-narrowing advice otherwise) — a silent truncation teaches the model nothing. (4) The timeout notice suggests a concrete next value instead of just reporting failure.
**Probe:** `tests/tool-guardrails.test.ts:15-70`: explicit-timeout precedence (:15), omission injects default (:19), disable ladder (:24), 60s built-in fallback (:30), small-output no-op (:34), disabled cap (:38), truncate+notice (:43), complete-last-line (:53), fullOutputPath mention (:63), image parts preserved (:70).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "capToolOutput resolveBashTimeout wireToolGuardrails", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt call-site timeout injection + result-site byte capping with codepoint/line-safe truncation and recovery-path notices. Adapt detection regexes to your host's timeout message. Omit the bash-only `details.fullOutputPath` linkage if your host lacks saved-full-output files — but then your notice must offer the redirect-to-file guidance instead.
