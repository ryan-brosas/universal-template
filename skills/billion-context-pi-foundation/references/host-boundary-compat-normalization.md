<!-- capsule-v2 -->
# Dual-host system-prompt compat — how does one codebase accept hosts whose system prompt is a string OR a string array?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** Where must string-vs-array host divergence be normalized so the rest of the code keeps a single interface?

## normalizeSystemPrompt at the two boundary points only
**Path/Symbol:** `src/compat.ts` (40L, whole): `normalizeSystemPrompt` (:14-18), `formatSystemPromptForEvent` (:25-31), `getSystemPromptText` (:37-40).
**Signature:** `normalizeSystemPrompt(input: string | string[] | undefined) -> string`; `formatSystemPromptForEvent(base, append) -> string` (join with `\n\n`); `getSystemPromptText(ctx) -> string`.
**Data Shape:** pi: `systemPrompt: string`, `getSystemPrompt(): string`; omp (oh-my-pi): both are `string[]`. Normalized form is always a newline-joined single string; undefined → "".

### Decisive source
```ts
// src/compat.ts:13-18 — the whole adapter in three lines
/** Normalize systemPrompt to a single string (join with newlines if array). */
export function normalizeSystemPrompt(input: string | string[] | undefined): string {
  if (input === undefined) return "";
  if (Array.isArray(input)) return input.join("\n");
  return input;
}
```

**Flow:** exactly two call sites need it — the `before_agent_start` handler appends the ACP doctrine via `formatSystemPromptForEvent(event.systemPrompt, prompt)` (index.ts :225-229), and the status command reads the effective prompt via `getSystemPromptText(ctx)` (commands.ts). Everywhere else the codebase handles plain strings. The module docstring states the contract explicitly: "These helpers normalize the differences so the rest of the codebase can work with a consistent string interface."
**Invariant:** (1) normalize at HOST BOUNDARIES, not deep inside logic — a porter who sprinkles Array.isArray checks through business logic doubles the divergence surface instead of quarantining it; (2) undefined must map to "" (not throw) because the append-site always concatenates; (3) joining with newlines preserves section semantics of array-form prompts (each element is a section).
**Probe:** `tests/compat.test.ts:14` ("formatSystemPromptForEvent preserves base prompt"); deterministic greps T12-T14 pin normalizeSystemPrompt's undefined/Array/string ladder and the exact two consumer sites (index.ts :26/:228, commands.ts :4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "normalizeSystemPrompt getSystemPromptText", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt boundary-quarantined normalization for any multi-host extension. Adapt the joined separator to your host's section semantics. Omit the dedicated module if your target is single-host — but keep the rule: one normalization point per host boundary, never inline type checks.
