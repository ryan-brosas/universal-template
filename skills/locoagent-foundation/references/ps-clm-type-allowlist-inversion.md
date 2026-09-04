<!-- capsule-v2 -->
# PS CLM type allowlist inversion — how do you gate .NET type literals without maintaining a dangerous-type denylist?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do you decide whether a .NET type literal appearing in a PowerShell command is safe, using Microsoft's own Constrained Language Mode research instead of enumerating dangerous types?

## Invert Microsoft's CLM allowlist: outside the set ⇒ ask
**Path/Symbol:** `src/tools/PowerShellTool/clmTypes.ts`:`CLM_ALLOWED_TYPES` (:18-188), `normalizeTypeName` (:194-203), `isClmAllowedType` (:209-211); consumer `powershellSecurity.ts`:`checkTypeLiterals` (:801-813) + `New-Object` branch (:360-427).
**Signature:** `function normalizeTypeName(name: string): string`; `function isClmAllowedType(typeName: string): boolean`.
**Data Shape:** `CLM_ALLOWED_TYPES: ReadonlySet<string>` of ~120 lowercase entries — short accelerator names AND full names where both exist (`int` + `system.int32`), because the AST emits the literal text (`[int]` → `"int"`, never resolved `System.Int32`). `parsed.typeLiterals?: string[]` collects every `TypeExpressionAst`/`TypeConstraintAst` FullName.

### Decisive source
```ts
// We invert this: type literals not in this set → ask. One canonical check
// replaces enumerating individual dangerous types (named pipes, reflection,
// process spawning, P/Invoke marshaling, etc.). Microsoft maintains the list.
export function normalizeTypeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\[\]$/, '')   // arrays of allowed types are allowed
    .replace(/\[.*\]$/, '') // generic WRAPPER checked, generic ARG ignored
    .trim()
}
```

**Flow:** parse script FindAlls both type-node kinds → TS receives raw literal names → `isClmAllowedType` normalizes → miss ⇒ ask with message naming the type. Two consumers: bracket syntax via `parsed.typeLiterals`, AND string-arg instantiation — `New-Object System.Net.WebClient` passes the type as a `StringConstantExpressionAst` argument that `typeLiterals` never sees, so `checkComObject` separately extracts -TypeName (colon-bound / space-separated / positional-0 past known value+switch params) and runs the SAME allowlist check.
**Invariant:** Security-critical REMOVALS from Microsoft's list are documented in-line: `adsi`/`adsisearcher` (LDAP network binds), `wmi`/`wmiclass`/`wmisearcher`/`cimsession` (+ their FQ forms, incl. DirectoryEntry/DirectorySearcher/ManagementObject/ManagementClass/ManagementObjectSearcher) — Microsoft allows them for trusted-domain admins; here the target host is unvalidated so casts like `[wmisearcher]'SELECT * FROM Win32_Process'` must prompt. Ordering matters in consumers: `checkTypeLiterals` runs AFTER broad member-invocation flagging so `[Reflection.Assembly]::Load` gets the PRECISE "outside the ConstrainedLanguage allowlist" message while pure casts like `[int]$x` (no member call) hit only this check. Generic normalization is conservative-by-design: outer type decides, args unchecked.
**Probe:** `grep -cF "'system.management.automation." src/tools/PowerShellTool/clmTypes.ts` → `10` (9 accelerator FQs + the comment line carrying the same prefix) and `grep -nF "'adsisearcher'" src/tools/PowerShellTool/clmTypes.ts` → :21, the REMOVAL COMMENT itself (the entry is absent from the set — absence-with-rationale is the invariant; anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "CLM_ALLOWED_TYPES normalizeTypeName isClmAllowedType", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the inversion (maintain an allowlist sourced from Microsoft's CLM doc, treat misses as ask) plus the dual-consumer requirement (bracket literals AND New-Object string args). Adapt the set when Microsoft updates CLM; keep the removal comments attached to entries. Omit the PowerShell-doc URL fetch behavior (static copy). Coverage caveat: no unit tests in-repo; coverage stdin-JSON reports `no_recorded_issue` for `src/tools/PowerShellTool/clmTypes.ts` at gen 2026-08-22T23:59Z.
