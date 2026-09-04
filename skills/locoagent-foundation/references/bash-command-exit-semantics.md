<!-- capsule-v2 -->
# Command exit semantics — grep-1 is not an error

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How should an agent shell interpret exit codes so informational failures don't read as tool errors?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/commandSemantics.ts` — `DEFAULT_SEMANTIC` (:22-26), `COMMAND_SEMANTICS` Map (:31-89: grep/rg/find/diff/test/[), `getCommandSemantic` (:94-99), `heuristicallyExtractBaseCommand` (:112-119), `interpretCommandResult` (:124+).
**Signature:** `interpretCommandResult(command, exitCode, stdout, stderr) → { isError, message? }`.
**Data Shape:** `CommandSemantic = (exitCode, stdout, stderr) → {isError, message?}` keyed by base command.

### Decisive source
```ts
// Many commands use exit codes to convey information other than just success/failure.
// For example, grep returns 1 when no matches are found, which is not an error condition.
```

**Flow:** extract base command from the LAST segment of a compound (the pipeline tail determines the exit code) via an explicitly untrusted heuristic ("May get it super wrong - don't depend on this for security") → table lookup: grep/rg ⇒ error only at ≥2 with "No matches found" at 1; find ⇒ ≥2, 1 = partial success (inaccessible dirs); diff/test/[ ⇒ ≥2 with meaning-bearing messages at 1; everything else default 0-is-success.

**Invariant:** (1) Exit-code interpretation is per-command POLICY, not arithmetic: 1 can be a successful negative answer. (2) The extractor is display/UX-tier only and says so in-source — never reuse a heuristic command-name grabber for security decisions (contrast the AST-resolved argv tier). (3) Message text carries the semantic ("Files differ") so downstream agents can react without re-running.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'not an error condition' src/tools/BashTool/commandSemantics.ts` → :5; `grep -nF 'depend on this for security' src/tools/BashTool/commandSemantics.ts` → :110; graph `search_graph --project locoagent --query interpretCommandResult` → :124-140 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "interpretCommandResult COMMAND_SEMANTICS CommandSemantic", limit: 5 });
```

## Verdict
Adopt the table-driven semantic map for agent-facing shells; extend per your toolset. Keep the security-tier separation explicit.
