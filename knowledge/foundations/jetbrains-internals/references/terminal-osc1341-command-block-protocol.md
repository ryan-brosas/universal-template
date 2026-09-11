<!-- capsule-v2 -->
# Terminal command-block protocol OSC 1341 - how does the IDE track commands, prompts, and even RPC round-trips inside an UNMODIFIED user shell?

**Source:** PhpStorm installed build PS-262.9437.196 (plugins/terminal/shell-integrations/); Codebase Memory project jetbrains-phpstorm. **Question:** If I port an IDE terminal that must segment output into command blocks and read shell state from any of bash/zsh/fish/PowerShell, what wire protocol and hook strategy survive hostile user configs?

## The private escape channel
**Path/Symbol:** bash/command-block-support-reworked.bash:35,48,52,75-79 (emit sites); :20-27 (__jetbrains_intellij_encode); bash/command-block-support.bash:91,121-123,145,148,151,187,285,293 (legacy emit set); every carrier sources BOTH generations unconditionally (bash-integration.bash:126-131, zsh-integration.zsh:62-65, fish-integration.fish:44-51, powershell-integration.ps1 hook invokes).
**Data Shape:** ESC ] 1341 ; <event>[;key=value ...] BEL. Payload values are HEX-encoded: od -An -tx1 -v piped through tr deleting whitespace, with a pure-bash byte-loop fallback pinned under LC_CTYPE=C LC_COLLATE=C (od-less systems). Events (census over this install): initialized{current_directory | shell_info=JSON}, command_started{command[,current_directory]}, command_finished{exit_code[,current_directory]}, prompt_started, prompt_finished, prompt_shown, aliases_received{result}, command_history{history_string}, prompt_state_updated{current_directory,user_name,user_home,git_branch,virtual_env,conda_env,original_prompt,original_right_prompt}, clear_invoked, shell_editor_buffer_reported{shell_editor_buffer}, generator_finished{request_id,result,exit_code}.

### Decisive source
```bash
[ -z "${INTELLIJ_TERMINAL_COMMAND_BLOCKS_REWORKED-}" ] && return   # generation gate
__jetbrains_intellij_command_preexec() {
  builtin local entered_command="${BASH_COMMAND:-}"
  builtin printf '\e]1341;command_started;command=%s\a' "$(__jetbrains_intellij_encode "$entered_command")"
  PS1="$__jetbrains_intellij_original_ps1"   # unwrap while running
}
```

**Flow:** two self-gated generations ship side-by-side per shell: command-block-support.* gates on INTELLIJ_TERMINAL_COMMAND_BLOCKS, command-block-support-reworked.* on INTELLIJ_TERMINAL_COMMAND_BLOCKS_REWORKED (probe: head -3 both files; grep finds reworked trio bash/fish/zsh; the ps1 twins match nothing because they are UTF-16). Legacy bash uses rcaloras/bash-preexec preexec_functions/precmd_functions; reworked bash installs a DEBUG trap that SAVES the original trap string (trap -p DEBUG parsed via eval into an array), fires preexec once behind a running-flag, always chains the original trap, and skips PROMPT_COMMAND-internal commands (Ctrl+C-at-prompt case sets should_update_prompt without emitting started). PS1 strategies differ deliberately: legacy REPLACES PS1 with the bare marker sequence (original stashed); rewrapped WRAPS the user PS1 with marker-emitting groups so the visible prompt survives.
**Invariant:** the channel is line-safe because payloads are hex; the host never parses unescaped tty text. The generator pair (run_generator request_id command -> eval -> generator_finished{request_id,result,exit_code}) is an IDE-to-shell RPC over the same stream: guarded out of started/finished events, added to HISTIGNORE, and bind-x editor-buffer reports are marked generator too (bind -x fires preexec unlike zsh bindkey). clear() is replaced (after unalias) to emit clear_invoked instead of clearing. Legacy-only fix_prompt_command_order moves bash-preexec hooks LAST in PROMPT_COMMAND (array form on bash >= 5.1) because their precmd runner lands FIRST otherwise and PS1 reads stale.
**Probe:** executed from install root (node v26.7.0 present; bash present): bash -n green on all five bash files; event census grep -rhoE 1341;[a-z_]+ over the tree returns exactly the vocabulary above with counts {initialized 4, command_started 4, command_finished 4, shell_editor_buffer_reported 2, prompt_state_updated 2, prompt_started 2, prompt_finished 2, generator_finished 2, command_history 2, clear_invoked 2, aliases_received 2, prompt_shown 1}; hex demo printf abc | od -An -tx1 -v | tr -d space == 616263. zsh NOT INSTALLED on this host: zsh-side behavior is whole-source-read verified only (runtime smoke BLOCKED, see work record).
**Coverage caveat:** index_status flags the ps1 scripts and zdotdir dotfiles parse_partial (UTF-16/dotfile parsing); they were validated by direct decode/read per the index-status instruction, not via graph symbols.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-phpstorm", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'plugins/terminal/shell-integrations' RETURN f.file_path ORDER BY path" });
```

## Verdict
Adopt OSC-1341-style private escape events + hex payloads verbatim for terminal-command tracking ports. Adapt the event subset to your features (start with the reworked six-event set; add prompt_state_updated only if you render remote prompt state). Omit the legacy/replaced-PS1 strategy unless you also ship a restore path - wrapping is strictly safer against user prompt frameworks.
