<!-- capsule-v2 -->
# Generator command channel — how does the IDE run a helper command INSIDE the interactive shell and get its output back without polluting history or blocks?

**Source:** JetBrains MPS install `MPS-261.25134.779`; `bash/command-block-support.bash:46-57,285-303`, `zsh/command-block-support.zsh:37-48,63-65`, ps1 classic `Clear-History`/`AddToHistoryHandler` plane; Codebase Memory project `jetbrains-mps`. **Question:** what is the request/response contract for in-shell evaluation, and how is internal traffic hidden from user-visible history?

## Connected graph-selected seam: run_generator + suppression hooks
**Path/Symbol:** `__jetbrains_intellij_run_generator` (.bash:50, .zsh:41); suppressors: bash HISTIGNORE appends (.bash:302-303), zsh `zshaddhistory` (.zsh:73-75), ps1 `Clear-History -CommandLine "__jetbrains_intellij_run_generator*"` (:60) + wrapped PSReadLine AddToHistoryHandler (:262-269).
**Signature:** `run_generator <request_id> <command>` -> emits frame `generator_finished;request_id=<id>;result=<hex>;exit_code=<n>`.
**Data Shape:** result captured as `$(eval "$command" 2>&1)` (stderr merged), hex-encoded; exit code of eval preserved via separate assignment (source comment: joining assignment with eval loses $?).

### Decisive source
```bash
__jetbrains_intellij_run_generator() {
  __JETBRAINS_INTELLIJ_GENERATOR_COMMAND=1
  builtin local request_id="$1" command="$2"
  # separate assignment so eval exit code is capturable
  builtin local result
  result="$(eval "$command" 2>&1)"
  builtin local exit_code=$?
  builtin printf '\e]1341;generator_finished;request_id=%s;result=%s;exit_code=%s\a' \
    "$request_id" "$(__jetbrains_intellij_encode "$result")" "$exit_code"
}
# suppression (bash): append-only, preserves user entries
HISTIGNORE="${HISTIGNORE-}:__jetbrains_intellij_run_generator*"
```

**Flow:** IDE writes the generator invocation into the shell stdin -> preexec sees a name-matching command and SKIPS command_started (generator flag checked first) -> precmd skips command_finished via same flag (bash/zsh) -> response rides back on the SAME OSC channel keyed by request_id.
**Invariant:** every internal command must be invisible on FOUR surfaces at once: block UI (flag skip), shell history (HISTIGNORE/zshaddhistory/Clear-History+AddToHistoryHandler per shell), and the readline buffer reporter must not self-trigger. The Esc-O editor-buffer binding is ALSO marked generator in bash specifically because `bind -x` fires PREEXEC/PRECMD while zsh bindkey widgets do NOT (.bash:285-294 comment) - the asymmetry is load-bearing.
**Probe (executed):** P9-fixed live call under gate: set c="echo hi" then `__jetbrains_intellij_run_generator req1 "$c"` -> od dump shows bytes `033 ] 1341 ; g e n e r a t o r _ f i n i s h e d ; r e q u e s t _ i d = r e q 1 ; r e s u l t = 6 8 6 9 ; e x i t _ c o d e = 0 \a` GREEN (`6869` = hex of "hi").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-mps", query: "run_generator request_id", limit: 5 });
// matches .bash/.zsh generator functions across both generations
```

**See also:** `terminal-osc1341-command-block-protocol.md` (base generator/RPC paragraph) and `terminal-osc1341-event-protocol.md` (verification harness); this capsule owns the live RPC execution and the four-surface suppression checklist.

**Coverage:** cited paths no_recorded_issue; probe executed byte-exact this pass.

## Verdict
Adopt: eval-with-request-id over an already-open side channel for IDE->shell queries (env census, alias map, directory listing all reuse it); the four-surface invisibility checklist. Adapt: marker prefix to your namespace; keep stderr merged into result like a terminal would show it. Omit: PowerShell Clear-History wildcard dance if your host has native history filters.
