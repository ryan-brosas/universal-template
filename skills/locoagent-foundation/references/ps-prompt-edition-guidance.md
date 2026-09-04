<!-- capsule-v2 -->
# PS prompt edition guidance — how does the tool's own system prompt prevent the model from emitting wrong-edition syntax?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What version-specific PowerShell guidance belongs in a tool prompt, and how is the unknown-edition case handled?

## Edition-conditional sections with conservative fallback
**Path/Symbol:** `src/tools/PowerShellTool/prompt.ts`:`getEditionSection` (:51-71), `getPrompt` (:73-145), `getSleepGuidance`/`getBackgroundUsageNote` (:26-44); edition source: `powershellDetection.getPowerShellEdition`.
**Signature:** `async function getPrompt(): Promise<string>`.
**Data Shape:** Three branches: desktop (5.1), core (7+), null ⇒ assume 5.1.

### Decisive source
```ts
if (edition === 'desktop') {
  return `PowerShell edition: Windows PowerShell 5.1 (powershell.exe)
   - Pipeline chain operators \`&&\` and \`||\` are NOT available — they cause a parser error. To run B only if A succeeds: \`A; if ($?) { B }\`. ...
   - Avoid \`2>&1\` on native executables. In 5.1, redirecting a native command's stderr ... sets \`$?\` to \`$false\` even when the exe returned exit code 0. ...
   - Default file encoding is UTF-16 LE (with BOM). ...`
}
// null => "unknown — assume Windows PowerShell 5.1 for compatibility"
```

**Flow:** prompt composes edition section + non-interactive hazards (Read-Host/Get-Credential hang under `-NonInteractive`; destructive cmdlets need `-Confirm:$false`) + here-string discipline (`'@` at column 0) + stop-parsing `--%` guidance + dedicated-tool redirection (don't use PS for file ops) + no-cd-prefix rule + background/sleep guidance gated by env.
**Invariant:** The 5.1 stderr-redirect `$?` trap documented here is the SAME fact that justifies the provider's `$LASTEXITCODE`-first exit capture (`ps-execution-provider-envelope.md`) — prompt guidance and exit semantics must agree. Unknown edition always degrades to the MORE restrictive syntax advice.
**Probe:** `grep -nF "assume Windows PowerShell 5.1 for compatibility" src/tools/PowerShellTool/prompt.ts` → :68 and `grep -nF 'sets \`$?\` to \`$false\` even when the exe returned exit code 0' src/tools/PowerShellTool/prompt.ts` → :56 (the 5.1 stderr-redirect `$?` trap; anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getEditionSection PowerShell edition desktop core", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt edition-conditional prompting with restrictive-default fallback and the hazard list. Adapt wording to your product voice. Omit env-var names for feature toggles. Coverage caveat: probes deterministic; no upstream tests.
