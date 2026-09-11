<!-- capsule-v2 -->
# Shell-startup injection ladders — how does an external program get its integration sourced FIRST inside bash/zsh/fish without stealing the user rcfile?

**Source:** JetBrains MPS install `MPS-261.25134.779`, `plugins/terminal/shell-integrations/{bash/bash-integration.bash, zsh/zdotdir/*, fish/fish-integration.fish}`; Codebase Memory project `jetbrains-mps`. **Question:** what is the exact startup-file choreography per shell so integration code loads after user config yet still wins prompt control?

## Connected graph-selected seam: entry-point scripts around the hook families
**Path/Symbol:** `bash/bash-integration.bash:1-135` whole ladder; `zsh/zdotdir/.zshenv` (scheme doc) + `zdotdir/.zshrc:10-29` + `source-original.zsh`; `fish/fish-integration.fish:1-50`.
**Signature:** none (scripts); env handoff variables: `JEDITERM_SOURCE`, `JEDITERM_SOURCE_ARGS`, `JEDITERM_SOURCE_SINGLE_ARG`, `JEDITERM_USER_RCFILE`, `LOGIN_SHELL`, `JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR`, `JETBRAINS_INTELLIJ_ZSH_DIR`, `__INTELLIJ_COMMAND_HISTFILE__`.
**Data Shape:** IDE spawns the shell with env instructions; scripts consume-and-unset each one exactly once.

### Decisive source (zdotdir .zshrc core)
```bash
# HISTFILE was set against the FAKE ZDOTDIR by /etc/zshrc - repair before user rc
HISTFILE="${JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR:-$HOME}/.zsh_history"
JETBRAINS_INTELLIJ_ORIGINAL_FILENAME_TO_SOURCE='.zshrc'
builtin source "$JETBRAINS_INTELLIJ_ZSH_DIR/zdotdir/source-original.zsh"
if [[ -n "${JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR-}" ]]; then
  ZDOTDIR="$JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR"; builtin unset JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR
else
  builtin unset ZDOTDIR   # default ZDOTDIR back to HOME
fi
builtin source "${JETBRAINS_INTELLIJ_ZSH_DIR}/zsh-integration.zsh"
```

**Flow:** zsh = point ZDOTDIR at the integration dir so EVERY standard startup file resolves there; .zshenv documents the goal (their precmd must append LAST to win PS1 control); their .zshrc repairs HISTFILE, sources the user real .zshrc through source-original.zsh, restores ZDOTDIR, then loads zsh-integration.zsh. bash = replay the login rc ladder manually (/etc/profile -> ~/.bash_profile -> ~/.bash_login -> ~/.profile, else ~/.bashrc at :13-30), then force-vars (:78), key bindings (:81-84), JEDITERM_USER_RCFILE (:89-92), JEDITERM_SOURCE (:98-106), configureCommandHistory EXIT-trap (:109-121), command-block-support variants LAST (:124-128). fish = consume JEDITERM_SOURCE first, apply force-vars, source both block-support variants.
**Invariant:** (1) user rcfiles run EXACTLY once even though ZDOTDIR was hijacked (the fake dir contains only stubs); (2) integration hooks register AFTER user plugins so add-zsh-hook/precmd_functions arrays execute them last — ordering is the control mechanism; (3) configureCommandHistory installs its EXIT trap ONLY if `[ -z "`trap -p EXIT`" ]` — never steal an existing trap; swaps HISTFILE only if the command-history file is non-empty.
**Probe (executed):** P3/P3b gate behavior on the downstream script; full ladder itself is spawn-side (IDE sets ZDOTDIR/JEDITERM_* before exec) — pinned by direct read of all three entry scripts plus the .zshenv scheme comment (:1-20).

## Posix-mode dance (bash-specific trap)
`disable_posix` (`set +o posix`, flag remembered) wraps ENV overriding and `bind` word-motion keys because posix mode breaks both; `restore_posix` runs BEFORE sourcing user rc AND as the last lines of the script, then both functions are unset (:34-46, :51, :87, :96, :133-135). Port as: any builtin-hostile shopt gets a save/toggle/restore bracket around non-user-owned code only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-mps", paths: ["plugins/terminal/shell-integrations/bash/bash-integration.bash", "plugins/terminal/shell-integrations/zsh/zdotdir/.zshrc"] });
// executed this pass: bash-integration no_recorded_issue; .zshrc parse_partial 5-34 (whole-file direct read done)
```

**Relationship:** `zdotdir-config-takeover-ladder.md` (PhpStorm source) owns the four-user-file preservation census for the zsh side; this MPS-source capsule keeps the whole-ladder view across bash+fish plus the posix bracket and history-trap guard.

**Coverage:** .zshrc is parse_partial 5-34 — cited from direct whole-file read (33 lines), not graph nodes.

## Verdict
Adopt: ZDOTDIR-style root redirection when a shell resolves config from one directory variable; manual rc-ladder replay when it does not; consume-once env handoff for arguments you cannot pass on the command line. Adapt: file names/order to your shells. Omit: IntelliJ variable names; the fish `exit`-vs-`return` compat note travels with fish ports only.
