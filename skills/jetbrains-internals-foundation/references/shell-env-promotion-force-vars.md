<!-- capsule-v2 -->
# Shell env-var promotion (_INTELLIJ_FORCE_SET_* / _INTELLIJ_FORCE_PREPEND_*) - how does a launcher inject environment into a user's interactive shell WITHOUT leaking into unrelated processes?

**Source:** PhpStorm installed build PS-262.9437.196; Codebase Memory project jetbrains-phpstorm. **Question:** How do you deliver env vars, a sourced script, and per-session history capture into a shell whose rc files you do not own?

## The promotion protocol
**Path/Symbol:** bash/bash-integration.bash:53-80 (override_jb_variables over env), :100-109 (JEDITERM_SOURCE(+_ARGS/_SINGLE_ARG)), :91-95 (JEDITERM_USER_RCFILE), :111-123 (__INTELLIJ_COMMAND_HISTFILE__); zsh/zsh-integration.zsh:14-47 ((P) indirect expansion over parameters module), :49-57 (self-removing precmd); fish/fish-integration.fish:6-40 (string sub -s 21/-s 25, PATH/CDPATH/MANPATH colon-split lists); powershell-integration.ps1:1-14 (Get-ChildItem env: scan).
**Signature:** promote(name): strip fixed-width prefix then export NAME=<payload>[ + existing]; unset prefixed original.
**Data Shape:** _INTELLIJ_FORCE_SET_<NAME>=<value> (20-char prefix) and _INTELLIJ_FORCE_PREPEND_<NAME>=<value> (24-char prefix). Offsets: bash substring 20/24 (0-based drop), fish string sub -s 21/-s 25 (1-based), pwsh -replace prefix. PREPEND concatenates value BEFORE current value.

### Decisive source
```bash
# For every _INTELLIJ_FORCE_PREPEND_FOO=BAR run: export FOO=BAR$FOO.
for ij_env_name in ${parameters[(I)_INTELLIJ_FORCE_PREPEND_*]}; do
  builtin local env_name="${ij_env_name:24}"
  builtin export "$env_name"="${(P)ij_env_name}${(P)env_name}"
  builtin unset "$ij_env_name"
done
```

**Flow:** the IDE exports ONLY prefixed variables into the child shell; each carrier promotes them at session-init time and unsets the prefixes so no underscored name ever escapes into the user's processes or tools like env-dumping prompts. Timing contract (zsh comments state it): promotion runs AFTER all user startup files but BEFORE other precmd hooks, so prompt frameworks (Powerlevel10k named in-comment) already see the activated venv. JEDITERM_SOURCE carries an extra script to source; JEDITERM_SOURCE_ARGS is either a list or ONE arg depending on JEDITERM_SOURCE_SINGLE_ARG (both shells branch on it); JEDITERM_USER_RCFILE sources the user's real rc ahead of integration. __INTELLIJ_COMMAND_HISTFILE__ converts into an EXIT trap (history -w file; HISTFILE=orig) installed ONLY when no EXIT trap exists, and HISTFILE swaps onto the session file only when it is non-empty - history capture that yields to existing traps.
**Invariant:** promotion consumes-and-unsets; the reserved prefix IS the namespace. Prefix widths are load-bearing constants (probe: wc -c == 20 and 24). fish treats PATH/CDPATH/MANPATH specially: value split on colons into fish LISTS before set -gx. pwsh runs JEDITERM_SOURCE with the call operator in child scope - the comment documents it can run code/export env vars but CANNOT export PS variables (dot-sourcing would be needed for that).
**Probe:** executed live in this run: printf %s '_INTELLIJ_FORCE_SET_' | wc -c == 20; '_INTELLIJ_FORCE_PREPEND_' == 24; and a live promotion env _INTELLIJ_FORCE_SET_PSTPROBE=hello bash -c loop applying substring offset printed PSTPROBE=hello.
**Coverage caveat:** none - plain text carriers fully indexed/readable.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm", query: "override_jb_variables configure_session", limit: 10 });
```

## Verdict
Adopt prefixed-env promotion whenever a parent process must configure an interactive shell it does not own. Adapt prefix text and offsets to your namespace. Omit direct env injection (pollutes children) and dot-sourced rc edits (hostile rc files break you).