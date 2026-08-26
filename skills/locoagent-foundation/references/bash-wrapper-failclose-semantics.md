<!-- capsule-v2 -->
# Wrapper stripping in checkSemantics — enumerate-or-fail-closed

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you see THROUGH safe wrappers (timeout/nice/env/stdbuf/nohup/time) to the wrapped command, without an unmodeled flag turning the wrapper name into a check-dodge?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/ast.ts` `checkSemantics` wrapper ladder (:2215-2384) then name gates (:2385-2458); twin representations that MUST stay in sync: string-level `stripSafeWrappers` (bashPermissions.ts :524-615) and argv-level `stripWrappersFromArgv` (:678-706).
**Signature:** iterative `a = argv; for(;;){ strip known wrapper else break }` ending at the wrapped name.
**Data Shape:** pure argv slices; no parsing — works on the RESOLVED SimpleCommand.argv.

### Decisive source
```ts
// SECURITY (PR #21503 round 3): a[i] exists but doesn't match our
// duration regex. GNU timeout parses via xstrtod() (libc strtod) and
// accepts `.5`, `+5`, `5e-1`, `inf`, `infinity`, hex floats — none
// of which match `/^\d+(\.\d+)?[smhd]?$/`. Empirically verified:
// `timeout .5 echo ok` works. Previously this branch `break`ed
// (fail-OPEN) so `timeout .5 eval "id"` with `Bash(timeout:*)` left
// name='timeout' and eval was never checked. Now fail CLOSED —
```

**Flow:** `time`/`nohup`: drop head (+optional `--`). `timeout`: walk GNU long flags (--foreground/--preserve-status/--verbose; --kill-after/--signal fused AND space-separated with `[A-Za-z0-9_.+-]` value allowlist), short (-v; -k/-s fused/separated), then REQUIRE a matching duration token — unknown flag OR non-matching duration ⇒ `{ok:false}` (never fall through with name='timeout'). `nice`: `-n N`, legacy `-N`, or bare; a[1] containing `$(` ⇒ reject (`nice $((0-5)) jq ...` would leave name='$((0-5))', :2304-2313). `env`: skip VAR=val, -i/-0/-v, `-u NAME`; ANY other flag (-S argv-splitter, -C altwd, -P altpath) ⇒ reject. `stdbuf`: iterate ALL flag forms (-o MODE / -o0 / --output=MODE); unknown ⇒ reject (the old slice(2) made `stdbuf --output 0 eval` resolve name='0', :2351-2354). Post-strip gates: empty argv[0] reject (unquoted-empty drops in bash while argv kept "", :2388-2400), placeholder argv[0] reject (defense-in-depth, :2402-2411), operator-prefix fragment reject (:2413-2420).

**Invariant:** (1) Every wrapper consumer (semantic checks, stripSafeWrappers, stripWrappersFromArgv) must recognize the SAME forms — the recorded asymmetry let `nice rm -rf /` become ask instead of deny under `Bash(rm:*)` and skipped the cd+git bare-repo gate (:543-551). (2) Unknown flag/duration ⇒ FAIL CLOSED, because you can no longer locate the wrapped command — falling through exposes the wrapper name to checks that then pass on the wrong argv[0]. (3) libc number parsing is wider than any regex you'll write: enumerate accepted forms explicitly and reject the rest. (4) Empty/runtime-determined argv[0] means every downstream check runs against a name bash never executes.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'cannot statically determine wrapped command' src/utils/bash/ast.ts` → :2312; `grep -nF 'fail closed on any unrecognized flag' src/utils/bash/ast.ts` → :2231; `grep -nF 'hid eval' src/utils/bash/ast.ts` → :2353; `grep -nF 'KEEP IN SYNC' src/tools/BashTool/bashPermissions.ts | head -1` → :675; graph `search_graph --project locoagent --query checkSemantics stripSafeWrappers` → ast.ts :2213-2679 / bashPermissions.ts :524-615 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "checkSemantics stripSafeWrappers stripWrappersFromArgv skipTimeoutFlags", limit: 5 });
```

## Verdict
Adopt the enumerate-known-forms-else-fail-closed wrapper ladder and mirror it in every consuming representation. Port the specific GNU flag tables as-is.
