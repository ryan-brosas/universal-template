<!-- capsule-v2 -->
# PS provider/UNC resolved-arg scan — why does the raw-string UNC check need an AST-args twin, and what must both defer to?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do you catch non-filesystem provider paths (`env:`, `HKLM:`) and credential-leaking UNC arguments when they hide behind backticks, colon-bound params, and unicode dashes?

## Raw pre-parse check + per-arg post-parse scan, both DEFERRED not early-returned
**Path/Symbol:** `src/tools/PowerShellTool/powershellPermissions.ts`: raw-string gate (:713-723), `NON_FS_PROVIDER_PATTERN` (:983-984), `extractProviderPathFromArg` (:985-1002 — dash-prefix colon strip + backtick strip), labeled `providerScan` loop (:1019-1041); shared detector `containsVulnerableUncPath` from `src/utils/shell/readOnlyCommandValidation.js`.
**Signature:** `function providerOrUncDecisionForArg(arg: string): PermissionResult | null`; pattern: `/^(?:[\w.]+\\)?(env|hklm|hkcu|function|alias|variable|cert|wsman|registry)::?/i`.
**Data Shape:** Scans `cmd.args` of every CommandAst (direct + nestedCommands); first match breaks via label.

### Decisive source
```ts
// The raw-string UNC check above (pre-parse) misses backtick-escaped forms;
// cmd.args has backtick escapes resolved by the parser. ...
// Provider prefix matches both the short form (`env:`, `HKLM:`) and the
// fully-qualified form (`Microsoft.PowerShell.Core\\Registry::HKLM\\...`).
// The optional `(?:[\\w.]+\\\\)?` handles the module-qualified prefix; `::?`
// matches either single-colon drive syntax or double-colon provider syntax.
```

**Flow:** pre-parse: `containsVulnerableUncPath(command)` on the RAW string catches obvious UNCs even without pwsh → result stored as a DEFERRED ask (early return here historically masked later sub-command denies). Post-parse: for each arg, strip a leading parameter prefix (unicode-dash aware, colon-bound value extraction) then backticks, test provider pattern, else re-test UNC → push ask. Both land in decisions[] where any deny still wins.
**Invariant:** Two layers exist because each sees different encodings (raw text vs parser-resolved args); neither may short-circuit past rule checks. UNC detection is about credential LEAKAGE (NTLM/Kerberos auto-auth on access), not just network I/O — hence also enforced inside path validation per extracted path.
**Probe:** `grep -nF "containsVulnerableUncPath" src/tools/PowerShellTool/powershellPermissions.ts | head -2` and `grep -nF "break providerScan" src/tools/PowerShellTool/powershellPermissions.ts | wc -l` → `2` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "providerOrUncDecisionForArg NON_FS_PROVIDER_PATTERN providerScan", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves powershellToolHasPermission :639-1648 containing the scan)*

## Verdict
Adopt dual-layer detection with deferral semantics. Adapt the provider list to your platform's PS drives. Omit module-name enumerations. Coverage caveat: probes deterministic; no upstream tests.
