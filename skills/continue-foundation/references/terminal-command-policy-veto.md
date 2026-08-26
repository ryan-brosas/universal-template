<!-- capsule-v2 -->
# Terminal-command policy veto — how does a shell tool downgrade its own permission to match command danger?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter make an `allowedWithPermission` terminal tool safe enough to auto-run benign commands while still blocking destructive ones outright?

## delegate to a security package; ladder is disabled-sticky / rm-rf-disables / network-escalates
**Path/Symbol:** `core/tools/definitions/runTerminalCommand.ts:63–72` (+ `defaultToolPolicy: "allowedWithPermission"` at :63); direct test `core/tools/implementations/runTerminalCommand.vitest.ts:740–860`.
**Signature:** `evaluateToolCallPolicy(basePolicy: ToolPolicy, parsedArgs: Record<string, unknown>): ToolPolicy` delegating to `evaluateTerminalCommandSecurity(basePolicy, parsedArgs.command)` from `@continuedev/terminal-security`.
**Data Shape:** in: base policy + raw command string (may be undefined/null/empty — handled gracefully); out: one of the three ToolPolicy values.

### Decisive source
```ts
defaultToolPolicy: "allowedWithPermission",
evaluateToolCallPolicy: (basePolicy, parsedArgs) => {
  return evaluateTerminalCommandSecurity(basePolicy, parsedArgs.command as string);
},
```
Direct-test-pinned behavior:
```
echo hello world   + allowedWithoutPermission ⇒ allowedWithoutPermission
ls -la             + allowedWithoutPermission ⇒ allowedWithoutPermission
rm -rf /           + allowedWithoutPermission ⇒ disabled          // destructive ⇒ hard disable
curl http://…      + allowedWithoutPermission ⇒ allowedWithPermission // network ⇒ escalate
echo test          + disabled                 ⇒ disabled          // user disable is STICKY
command: undefined/null/""                    ⇒ base kept         // graceful
```

**Flow:** unlike the five file tools (which resolve paths in preprocessArgs first), the terminal tool needs no preprocessing — the command string IS the decision input. The security classifier lives in a dedicated package so the same ladder can be reused by CLI/extension hosts; core only wires it into the tool definition. The client-side display layer additionally extracts `parsedArgs.command` as `displayValue` server-side (core.ts:1066–1068) so permission prompts show WHAT will run.
**Invariant:** user-set `disabled` survives every command evaluation (sticky), and evaluation can only make the outcome MORE restrictive than base — never less. Malformed args degrade to base policy rather than throwing.
**Probe:** `core/tools/implementations/runTerminalCommand.vitest.ts` describe block `runTerminalCommandTool.evaluateToolCallPolicy` (:740–860, 10 cases) pins the exact ladder above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "runTerminalCommand evaluateToolCallPolicy terminal security", limit: 10 });
```

## Verdict
Adopt the sticky-disabled + monotone-escalation contract and keep the classifier in its own importable unit; adapt the dangerous/network command lists to your threat model; omit Continue's specific cmd-lists as editable data. Caveat: the classifier body lives in the external `@continuedev/terminal-security` package (not indexed in this graph) — the REPO-SIDE contract is exactly the test-pinned surface above.
