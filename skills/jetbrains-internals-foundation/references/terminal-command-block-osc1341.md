<!-- capsule-v2 -->
# Terminal command-block protocol (OSC 1341) — how does an IDE bracket interactive shell commands into blocks using only escape sequences, with no user rc-file edits?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (not a git checkout; pin = product-info.json buildNumber); Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Shell-integration hook pair emitting a private OSC channel
**Path/Symbol:** `plugins/terminal/shell-integrations/zsh/command-block-support.zsh`: `__jetbrains_intellij_command_preexec` (:77-88), `__jetbrains_intellij_command_precmd` (:94-123), `__jetbrains_intellij_run_generator` (:34-45); bash twin `plugins/terminal/shell-integrations/bash/command-block-support.bash` (`command_started` :108-124, PS1 trick :89-100). Reworked generation: `*/command-block-support-reworked.{zsh,bash}`.
**Signature:** zsh: `add-zsh-hook preexec __jetbrains_intellij_command_preexec; add-zsh-hook precmd __jetbrains_intellij_command_precmd; add-zsh-hook zshaddhistory __jetbrains_intellij_zshaddhistory`. Wire events are OSC 1341: `\e]1341;<event>;k=<hex>;…\a`.
**Data Shape:** events observed: `command_started{command,current_directory}`, `command_finished{exit_code[,current_directory]}`, `initialized{shell_info|current_directory}`, `command_history{history_string}`, `prompt_state_updated{current_directory,user_name,user_home,git_branch,virtual_env,conda_env,original_prompt,original_right_prompt}`, `generator_finished{request_id,result,exit_code}`, `clear_invoked`, bash-only `prompt_shown` (embedded in PS1). All variable payloads hex-encoded (`od -An -tx1 -v | tr -d space` fast path; per-char `printf -v %02X` builtin fallback).

### Decisive source
\`\`\`zsh
# zsh command-block-support.zsh — first precmd is INITIALIZATION, not a user command:
__jetbrains_intellij_command_precmd() {
  builtin local LAST_EXIT_CODE="$?"
  if [[ -z "${__jetbrains_intellij_initialized-}" ]]; then
    # As `precmd` is executed before each prompt, for the first time it is called after
    # all rc files have been processed and before the first prompt is displayed.
    __jetbrains_intellij_initialized=1
    builtin printf '\e]1341;command_history;history_string=%s\a' "$(__jetbrains_intellij_encode_large "$(builtin history 1)")"
    … builtin printf '\e]1341;initialized;shell_info=%s\a' …
    builtin return
  fi
  … builtin printf '\e]1341;command_finished;exit_code=%s\a' "$LAST_EXIT_CODE"
  builtin print "${JETBRAINS_INTELLIJ_COMMAND_END_MARKER:-}"
}
# generator commands bypass blocks AND history:
__jetbrains_intellij_zshaddhistory() { ! __jetbrains_intellij_is_generator_command "$1"; }
\`\`\`

\`\`\`bash
# bash twin — invisible prompt event via PS1 (chars wrapped in \[ \] so width math ignores it):
__JETBRAINS_INTELLIJ_PS1='\[\e]1341;prompt_shown\a\]'
# started uses BOTH the typed command ($1) and Bash's resolved $BASH_COMMAND (alias value),
# skipping when the resolved command is an internal generator:
if __jetbrains_intellij_is_generator_command "$bash_command"; then return 0; fi
\`\`\`

**Flow:** IDE sets env gate → sources script from its own shell-stub (zdotdir/.bashrc) → script returns immediately if gate unset, else unsets gate (one-shot) → hooks registered → first precmd emits history+shell_info+`initialized` then end marker (init block) → every real command: preexec→`command_started`, precmd→`command_finished{exit_code}` + end marker + prompt state → IDE pairs events into blocks.
**Invariant:** (1) the FIRST precmd must be treated as init or you mint a phantom block; (2) generator/self-reporting commands must be excluded from both history and block pairing (flag var checked in three hooks); (3) payloads must be encoded so raw text can't forge or break the OSC envelope; (4) the reworked generation bails out entirely under powerlevel10k (`[ -n "${P9K_VERSION:-}" ] && return 0`) and restores the original PS1 during command runs — two generations differ by env gate name, never coexist.
**Probe:** `bash -n plugins/terminal/shell-integrations/bash/command-block-support.bash` → OK (executed). Content pins (executed): grep -c '1341' = 8 (zsh classic) / 9 (bash classic) / 6 (zsh reworked); gates `INTELLIJ_TERMINAL_COMMAND_BLOCKS` vs `INTELLIJ_TERMINAL_COMMAND_BLOCKS_REWORKED`; P9K guard present once in reworked. zsh interpreter NOT installed on host → zsh-side syntax check impossible (recorded block).

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "shell integration command block", limit: 8 });
// rank-1: bash-integration.bash configureCommandHistory :111-122; command-block-support preexec/precmd rows follow
\`\`\`

## Verdict
Adopt the OSC side-channel protocol shape: private OSC code + event grammar + hex payloads + init-block special case + generator exclusion — portable to any terminal emulator/host pairing. Adapt the hook registration per shell (add-zsh-hook vs bash-preexec library dependency at :6-15) and the prompt-event trick (PS1 embedding works only where PS1 is evaluated). Omit JetBrains-specific census payloads (shell_info JSON of oh-my-zsh/starship detection) unless your host needs prompt-replacement forensics.
