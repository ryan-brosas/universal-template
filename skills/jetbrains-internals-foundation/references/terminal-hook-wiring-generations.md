<!-- capsule-v2 -->
# Terminal hook-wiring generations — how do you intercept every command in bash/zsh/fish/PowerShell without breaking user hooks?

**Source:** JetBrains MPS install `MPS-261.25134.779`, `plugins/terminal/shell-integrations/`; Codebase Memory project `jetbrains-mps`. **Question:** which hook mechanism per shell is safe to compose with arbitrary user rcfiles, and what breaks when you choose wrong?

## Connected graph-selected seam: classic vs reworked families (two files per shell, two env gates)
**Path/Symbol:** classic `bash/command-block-support.bash:300-301` (`preexec_functions+=(__jetbrains_intellij_command_started)` / `precmd_functions+=(__jetbrains_intellij_command_terminated)`) vs reworked `bash/command-block-support-reworked.bash:82-113` (DEBUG-trap wrap); zsh trio `.zsh:220-222` (`add-zsh-hook preexec/precmd/zshaddhistory`); fish events `.fish:14,22`; ps1 `Rename-Item Function:\Prompt` + `PSConsoleHostReadLine` override.
**Signature:** reworked core: `trap '__jetbrains_intellij_debug_trap "$_"' DEBUG` set AFTER capturing the previous trap string.
**Data Shape:** state lives in globals (`__jetbrains_intellij_initialized`, `__jetbrains_intellij_command_running`, `__jetbrains_intellij_should_update_prompt`, ps1 `$Global:__JetBrainsIntellijState` hashtable with IsInitialized/IsCommandRunning/OriginalPSConsoleHostReadLine).

### Decisive source (reworked DEBUG-trap wrapper)
```bash
__jetbrains_intellij_debug_trap() {
  if __jetbrains_intellij_is_prompt_command_contains "${BASH_COMMAND:-}"; then
    # executing inside PROMPT_COMMAND - not a user command; still refresh prompt later
    __jetbrains_intellij_should_update_prompt="1"
    __jetbrains_intellij_run_original_debug_trap; return
  fi
  # DEBUG trap fires per simple command - handle only the first
  if [[ -n "$__jetbrains_intellij_command_running" ]]; then
    __jetbrains_intellij_run_original_debug_trap; return
  fi
  __jetbrains_intellij_command_preexec
  __jetbrains_intellij_run_original_debug_trap
}
__jetbrains_intellij_get_debug_trap() {   # parse `trap -- '<code>' DEBUG` back into code
  builtin local -a values
  builtin eval "values=($(trap -p "DEBUG"))"
  builtin printf '%s' "${values[2]:-}"
}
```

**Flow:** classic = register into shell-native hook arrays (via vendored bash-preexec for bash), REPLACE PS1 with an invisible OSC emitter, replay history+shell_info on first precmd. Reworked = wrap the DEBUG trap (bash), bracket PS1 between prompt_started/prompt_finished emitters, restore original PS1 during command run, no history replay.
**Invariant:** (1) a wrapper trap MUST always re-run the captured original (eval of `${values[2]}`), or user debugging integrations die; (2) DEBUG fires per pipeline element - the running-flag guard yields exactly one command_started; (3) PROMPT_COMMAND-internal executions must NOT count as commands (containment check splits on newline/semicolon, trims whitespace). Probe P8 executed the capture trick: set `trap ":" DEBUG` -> parsed value `[:]` GREEN.
**Probe (executed):** gate probes P3/P3b - sourcing classic .bash WITHOUT `INTELLIJ_TERMINAL_COMMAND_BLOCKS` defines NO functions and exits 0; WITH it, `type -t __jetbrains_intellij_command_terminated` -> `function`. (bind -x warns "line editing not enabled" under non-interactive bash - degrades gracefully.)

## Per-shell composition rules worth porting
- bash classic must REORDER PROMPT_COMMAND once (`fix_prompt_command_order`, .bash:236-282): bash-preexec prepends `__bp_precmd_invoke_cmd`, so PS1-mutating plugin hooks would run AFTER our terminated-hook and we would read a STALE PS1; fix strips those two tokens (string form AND array form for bash>=5.1) and re-appends them at the END.
- zsh: `zle -N` widget registration is REQUIRED before bindkey (:212-218); Esc-O binding reports `$BUFFER`; p10k Instant Prompt disabled via `POWERLEVEL9K_INSTANT_PROMPT=off` (:226, IJPL-101617) because it renders a prompt before .zshrc completes and desynchronizes block accounting.
- zsh history filter: `zshaddhistory` hook returning false on generator commands keeps internal traffic out of HISTFILE (.zsh:73-75).
- fish: event model `--on-event fish_preexec` / `--on-event fish_prompt`; the initializer ERASES ITSELF (`functions --erase __jetbrains_intellij_initialize`, .fish:28) and installs `command_finished` in its place - one-shot bootstrap pattern; top-level early-exit uses `exit` not `return` (Fish >=3.4 requirement noted in source).
- PowerShell: capture-and-rename `Function:\Prompt` (or synthesize an empty original), override `PSConsoleHostReadLine` to emit command_started ONLY when the returned line is non-empty (bare Enter/Ctrl+C are not commands), and restore `$Global:?` around calling the original prompt via a swallowed `Write-Error -ErrorAction ignore` hack so the user prompt sees real success state.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "jetbrains-mps", function_name: "jetbrains-mps.plugins.terminal.shell-integrations.bash.command-block-support-reworked.__jetbrains_intellij_command_preexec", direction: "outbound", depth: 2 });
// executed this pass: callees_total=2 -> encode(1), encode_slow(2)
```

**See also:** `terminal-osc1341-command-block-protocol.md` owns the base frame grammar and generation-gate survey; this capsule owns the per-shell composition rules.

**Coverage:** cited paths `no_recorded_issue`; behavior evidence limited to bash (only shell runtime installed on host) - zsh/fish/ps1 wiring claims are direct-read + graph evidence, marked as such.

## Verdict
Adopt: the generation split as a decision table - native hook arrays when the shell has them (zsh/fish), DEBUG-trap wrapping only when it does not (bash without a bash-preexec dependency), readline/prompt-function overrides for PSReadLine shells; always compose, never clobber originals. Adapt: gate env names and global prefixes per host. Omit: bash-preexec vendoring details (upstream rcaloras library rides along) unless you need its exact PROMPT_COMMAND contract.
