<!-- capsule-v2 -->
# Pre-execution regex security battery — bashCommandIsSafe legacy gate

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When no AST exists, what is the minimal fail-closed screen a command must pass before execution?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashSecurity.ts` — `bashCommandIsSafe_DEPRECATED` (:2257), async wrapper `bashCommandIsSafeAsync_DEPRECATED`/`bashCommandIsSafeAsync` (:2426+), safe-heredoc remainder re-check consumed at bashPermissions.ts :2098-2140; divergence counter callback (`onDivergence`) consumed in bashToolHasPermission :2352-2374.
**Signature:** `bashCommandIsSafeAsync(cmd, onDivergence?) → { behavior: 'passthrough'|'ask'|..., message?, isBashSecurityCheckForMisparsing? }`.
**Data Shape:** result carries the misparsing flag so callers can distinguish "regex tier couldn't parse" from "found danger".

### Decisive source
```ts
// Compound commands with safe heredoc patterns ($(cat <<'EOF'...EOF))
// trigger the $() check on the unsplit command. Strip the safe heredocs
// and re-check the remainder — if other misparsing patterns exist
// (e.g. backslash-escaped operators), they must still block.
```

**Flow:** run the 23-check battery (see bash-security-check-battery) over quote-projections of the unsplit command; on a MISPARSING ask, try the remainder after stripping RECOGNIZED-safe heredoc substitutions — if the remainder STILL asks as misparsing (or stripping failed), block with exact-match allow honored first; genuine dangerous-pattern asks never get the second chance. In the modern ladder this whole tier runs ONLY when AST subcommands are null, and per-subcommand reruns batch their divergence counts into one telemetry event (the per-sub `/proc/self/stat` read was measured as the hot-path driver).

**Invariant:** (1) Fail-closed means misparse ⇒ ask, but EXPLICIT user allows for that exact command outrank the heuristic — conscious choice wins. (2) Safe-pattern stripping must be narrow and re-checked: only recognized-safe heredocs earn a remainder retry. (3) Telemetry hot paths belong behind aggregation callbacks, not per-item events. (4) The `_DEPRECATED` suffix marks tier position, not dead code — it's still load-bearing when tree-sitter is off.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'must still block' src/tools/BashTool/bashPermissions.ts` → :2099; `grep -nF 'isBashSecurityCheckForMisparsing' src/tools/BashTool/bashSecurity.ts | head -1` → :962; graph resolves both entry points :2257 / :2426 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "bashCommandIsSafeAsync stripSafeHeredocSubstitutions", limit: 5 });
```

## Verdict
Adopt as the no-parser fallback shape: battery → safe-strip → re-check → explicit-allow override, with aggregated divergence telemetry.
