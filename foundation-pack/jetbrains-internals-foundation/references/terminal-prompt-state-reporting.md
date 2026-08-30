<!-- capsule-v2 -->
# Prompt-state reporting — how does an external program reconstruct what the user prompt WOULD have rendered, including framework themes?

**Source:** JetBrains MPS install `MPS-261.25134.779`; `bash/command-block-support.bash:91-107,156-266`, `zsh/command-block-support.zsh:125-199`; Codebase Memory project `jetbrains-mps`. **Question:** how do you capture the ORIGINAL prompt, expand its escapes safely, and fingerprint prompt frameworks - without rendering anything yourself?

## Connected graph-selected seam: configure_prompt / report_prompt_state / collect_shell_info trio
**Path/Symbol:** `.bash:91` PS1 constant; `configure_prompt` :93; `report_prompt_state` :156; `collect_shell_info` :198; zsh twins :125/:160.
**Signature:** emits `prompt_state_updated;current_directory=..;user_name=..;user_home=..;git_branch=..;virtual_env=..;conda_env=..;original_prompt=<hex>;original_right_prompt=<hex>`.
**Data Shape:** original PS1 saved BEFORE replacement; expansion via `${prompt@P}` (bash>=4.4) or subshell fallback; right prompt empty in bash (no RPROMPT concept).

### Decisive source (expansion ladder)
```bash
# Prompt expansion was introduced in 4.4 version of Bash
if [[ -n "${BASH_VERSINFO-}" ]] && (( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 4) )); then
  expanded_prompt=${prompt@P}
else
  # Launch a subshell with a desired prompt, then parse the output
  expanded_prompt=$(PS1="$prompt" "$BASH" --norc -i </dev/null 2>&1 | sed -n '${s/^\(.*\)exit$/\1/p;}')
fi
```

**Flow:** on load, remember user PS1 -> replace PS1 with invisible emitter (classic) or bracket it (reworked) -> after each command, re-expand the SAVED original and ship it plus environment facts (PWD/USER/HOME, git branch via `symbolic-ref --short HEAD || rev-parse --short HEAD`, VIRTUAL_ENV, CONDA_DEFAULT_ENV) -> IDE renders ITS OWN block decoration from the reported truth instead of scraping the screen.
**Invariant:** never expand the INJECTED PS1 - always the saved original; git branch falls back symbol-ref->short-hash so detached heads still report; framework detection is presence-of-marker-vars only (OSH_THEME/STARSHIP_START_TIME/BASH_IT_THEME/POSH_PID...; zsh adds ZSH_THEME/P9K_VERSION/SPACESHIP_*/ZPREZTODIR + `zstyle -s :prezto:module:prompt theme`) - zero probing of external processes.
**Probe (executed):** P11 expansion primitive: `PS1=abc:; printf "%s\n" "${PS1@P}"` -> `abc:` GREEN (version-gated @P path); subshell fallback cited read-only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-mps", qualified_name: "jetbrains-mps.plugins.terminal.shell-integrations.bash.command-block-support.__jetbrains_intellij_report_prompt_state" });
```

**Relationship:** wire grammar lives in `terminal-osc1341-command-block-protocol.md` (PhpStorm) / `terminal-command-block-osc1341.md` (WebStorm); this MPS-source capsule owns the reconstruction logic — expansion ladder, saved-original discipline, framework census.

**Coverage:** cited paths no_recorded_issue; zsh twin read directly; fish ships a REDUCED variant (PWD-only prompt_state_updated, .fish:37-39) - degrade gracefully when a shell lacks expansion primitives.

## Verdict
Adopt: save-then-replace (or bracket) prompt ownership + version-gated expansion ladder + marker-var framework census as the whole reconstruction contract. Adapt: parameter list to whatever your UI needs; add right-prompt only where the shell has one. Omit: oh-my-zsh/starship theme VALUES (only presence booleans are reported - respect privacy surface).
