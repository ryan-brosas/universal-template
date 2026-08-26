<!-- capsule-v2 -->
# PS AST parse spawn budget — how do you parse a PowerShell command's AST from Node when parsing itself spawns pwsh, and what happens to permission decisions when the parse fails?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do you parse an arbitrary PowerShell command's AST safely from Node when the parse itself must spawn pwsh — including argv-budget math, timeout/retry policy, cache-eviction policy, and the fail-degraded decision semantics?

## Spawn-based native parser with a derived argv budget
**Path/Symbol:** `src/utils/powershell/parser.ts`:`parsePowerShellCommandImpl` (:1136-1261), `WINDOWS_MAX_COMMAND_LENGTH` derivation (:611-641), `PARSE_SCRIPT_BODY` (:315-568), `TRANSIENT_ERROR_IDS` (:1267-1273).
**Signature:** `async function parsePowerShellCommandImpl(command: string): Promise<ParsedPowerShellCommand>` (memoized as `parsePowerShellCommand`, LRU 256 keyed on the exact command string).
**Data Shape:** In: raw command text. Out: `{ valid, errors[], statements[], variables[], hasStopParsing, originalCommand, typeLiterals?, hasUsingStatements?, hasScriptRequirements? }`. On ANY infrastructure failure the result is `valid:false` plus a typed `errors[0].errorId` (`NoInput`/`CommandTooLong`/`NoPowerShell`/`PwshSpawnError`/`PwshTimeout`/`PwshError`/`EmptyOutput`/`InvalidJson`).

### Decisive source
```ts
const SCRIPT_CHARS_BUDGET = ((WINDOWS_ARGV_CAP - FIXED_ARGV_OVERHEAD) * 3) / 8
const CMD_B64_BUDGET =
  SCRIPT_CHARS_BUDGET - PARSE_SCRIPT_BODY.length - ENCODED_CMD_WRAPPER
export const WINDOWS_MAX_COMMAND_LENGTH = Math.max(
  0,
  Math.floor((CMD_B64_BUDGET * 3) / 4) - SAFETY_MARGIN,
)
const UNIX_MAX_COMMAND_LENGTH = 4_500
export const MAX_COMMAND_LENGTH =
  process.platform === 'win32'
    ? WINDOWS_MAX_COMMAND_LENGTH
    : UNIX_MAX_COMMAND_LENGTH
// ...inside the impl:
const commandBytes = Buffer.byteLength(command, 'utf8')
if (commandBytes > MAX_COMMAND_LENGTH) {
```

**Flow:** length gate (UTF-8 BYTES) → cached pwsh discovery → wrap `$EncodedCommand = '<utf8-base64>'\n` + inline `PARSE_SCRIPT_BODY` → encode WHOLE script as UTF-16LE base64 → `pwsh -NoProfile -NonInteractive -NoLogo -EncodedCommand <b64>` → execa with 5 s timeout (env `CLAUDE_CODE_PWSH_PARSE_TIMEOUT_MS` override, read inside the impl not at module load) → ONE retry on timeout → JSON stdout through `ensureArray` (PS 5.1 `ConvertTo-Json` unwraps single-element arrays) → `transformRawOutput`.
**Invariant:** The Windows budget is DERIVED from `PARSE_SCRIPT_BODY.length` so it cannot go stale as the script grows, and the gate measures `Buffer.byteLength(command,'utf8')` — never `.length`. A BMP CJK char is 1 UTF-16 code unit but 3 UTF-8 bytes; comparing `.length` permits ~3× overflow → CreateProcess fails → `valid:false` → every deny rule silently degrades to ask (upstream finding #36). The Unix limit stays 4,500 DELIBERATELY: applying the Windows-derived cap (~1 KB for multibyte) on Unix would reject 1–4.5 KB compound scripts whose buried cmdlets carry user deny rules — a deny→ask regression. Parse failure is itself a security event: `powershellCommandIsSafe` returns `ask` for `!parsed.valid`, so anything that breaks parsing (timeout, missing pwsh, bad JSON, oversized command) downgrades deterministic denies to prompts.
**Probe:** `grep -nF "WINDOWS_MAX_COMMAND_LENGTH = Math.max" src/utils/powershell/parser.ts` (derivation site exists; anchored at the locoagent repo root) and `grep -cF "Process-BlockStatements -Block $ast." src/utils/powershell/parser.ts` → `5` (Begin/Process/End/Clean/DynamicParam all walked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "parsePowerShellCommandImpl EncodedCommand timeout retry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the derived-byte-budget pattern (budget computed FROM the payload constant, byte-length gate, platform-split caps, typed transient-error taxonomy with post-resolution LRU eviction so `PwshSpawnError/PwshError/PwshTimeout/EmptyOutput/InvalidJson` retry while deterministic failures cache). Adapt the execa dependency and the env-var name. Omit the upstream CI lore (JIT warm-up, Windows shard run ids). Coverage caveat: no unit tests ship in this repo (`tests/` holds shell scripts only) — probes are deterministic source pins; `check_index_coverage` on `src/utils/powershell/parser.ts` reports `no_recorded_issue`/`metadata_match` at generation 2026-08-22T23:59Z.
