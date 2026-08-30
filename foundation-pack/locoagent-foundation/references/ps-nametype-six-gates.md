<!-- capsule-v2 -->
# PS nameType gate six sites — why does every auto-allow path re-check nameType even after the rule matched?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Where must an "is this really a cmdlet, not a script path" gate be enforced so a stripped module prefix can never smuggle a local file execution through an allowlist match?

## Six enforcement sites; input-side stripping is unconditional, so every consumer gates
**Path/Symbol:** `src/tools/PowerShellTool/powershellPermissions.ts`: parse-failed exact-allow guard (:750-757), safe-output classification inside `getSubCommandsForPermissionCheck` (:582-585), exact-allow decision (:1306-1316), step-5 filter keeps applications (:1388-1390), user-rule continue gate (:1466-1470), application-with-rule approval fallthrough (:1493-1503); plus `modeValidation.ts` (:273-278 main loop, :366-371 nested) and `readOnlyValidation.ts`:`isAllowlistedCommand` (:1322-1333).
**Signature:** gate condition everywhere: `element.nameType !== 'application'` (+ `SAFE_EXTERNAL_EXES` bypass keyed on the RAW first token of `cmd.text`).
**Data Shape:** `nameType` ∈ `'cmdlet' | 'application' | 'unknown'`, computed from the RAW pre-strip name (`ps-name-resolution-spoof-gates.md`).

### Decisive source
```ts
// SECURITY: INPUT-side stripModulePrefix is unconditional, so
// `scripts\\Get-Content /etc/shadow` strips to 'Get-Content' and matches
// an allow rule `Get-Content:*`. Without the nameType guard, continue
// skips all checks and the local script runs. nameType is classified from
// the RAW name pre-strip — `scripts\\Get-Content` → 'application' (has `\\`).
if (
  subResult.behavior === 'allow' &&
  element.nameType !== 'application' &&
  !hasSymlinkCreate
) {
```

**Flow:** because canonicalization strips `Module\Name`, quotes, and PATHEXT for MATCHING, any site that turns a match into silent progress (auto-allow, filtering out of approval lists, `continue`) must independently verify the RAW name was not path-like. The sites cover: exact allow (both parse states), safe-output filtering (a `scripts\Out-Null` would otherwise vanish from the approval list), compound filter retention, user allow rules, and the allowlist lookup itself (where `where.exe` is the sole bypass, matched against `cmd.text`'s raw first token so `scripts\where.exe` stays blocked).
**Invariant:** Filtering-out-of-a-list IS auto-allow — anything removed from approval must pass the same nameType gate as positive allow paths. Module-qualified cmdlets (`Microsoft.PowerShell.Management\Get-ChildItem`) also classify `'application'` and prompt: accepted collateral damage, fail-safe direction.
**Probe:** `grep -cF "nameType !== 'application'" src/tools/PowerShellTool/powershellPermissions.ts` → `5` and `grep -cF "nameType === 'application'" src/tools/PowerShellTool/modeValidation.ts` → `2` and `grep -nF "const SAFE_EXTERNAL_EXES = new Set(['where.exe'])" src/tools/PowerShellTool/readOnlyValidation.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isAllowlistedCommand nameType application where.exe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the principle (gate at every consumption point of a stripped name; classify from raw) rather than memorizing six line numbers — new allow paths need a NEW gate. Adapt the classifier regex to your host. Omit module-qualified UX discussion beyond the accepted-prompt note. Coverage caveat: probes are deterministic source pins (no upstream tests); graph confirms `isAllowlistedCommand` :1310-1516.
