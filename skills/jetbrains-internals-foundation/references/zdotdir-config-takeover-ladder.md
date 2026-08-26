<!-- capsule-v2 -->
# ZDOTDIR takeover ladder - how do you hook zsh startup WITHOUT losing any of the user's four config files?

**Source:** PhpStorm installed build PS-262.9437.196 (plugins/terminal/shell-integrations/zsh/zdotdir/{.zshenv,.zprofile,.zshrc,source-original.zsh}); Codebase Memory project jetbrains-phpstorm. **Question:** zsh reads config ONLY from $ZDOTDIR - how does an embedder intercept startup while the user's own .zshenv/.zprofile/.zshrc/.zlogin still run, in order, unmodified?

## The takeover chain
**Path/Symbol:** .zshenv:9-25 (documented startup-file order + rationale: custom-ZDOTDIR launch prevents user configs from being read, so each counterpart sources the original manually), :46-47 (source-original helper call); .zshrc:9-12 (HISTFILE correction BEFORE sourcing user .zshrc because etc/zshrc computed it from the hijacked ZDOTDIR), :17-25 (restore real ZDOTDIR so zsh itself reads .zlogin next), :27-29 (integration sourced last); source-original.zsh:10-39 (global-scope loader).
**Signature:** source_original(filename): guard -> swap ZDOTDIR back -> source ORIGINAL_ZDOTDIR/filename -> capture user-side ZDOTDIR changes as new ORIGINAL -> restore hijack dir.

### Decisive source
```zsh
# prevent recursion, just in case
if [[ "$ZDOTDIR" != "${JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR:-$HOME}" ]]; then
  JETBRAINS_INTELLIJ_ZDOTDIR_COPY="$ZDOTDIR"
  # Correct ZDOTDIR before sourcing the user's file as it might rely on the value of ZDOTDIR.
  builtin source "$JETBRAINS_INTELLIJ_ORIGINAL_FILE"
  # ZDOTDIR might be changed by the user config
  if [[ -n "$ZDOTDIR" ]]; then JETBRAINS_INTELLIJ_ORIGINAL_ZDOTDIR="$ZDOTDIR"; fi
  ZDOTDIR="$JETBRAINS_INTELLIJ_ZDOTDIR_COPY"   # back to IntelliJ location
fi
```

**Flow:** launch zsh with ZDOTDIR pointing INTO the install. The hijacked .zshenv sources the user's ~/.zshenv through the helper; the hijacked .zprofile/.zshrc repeat per stage. The helper runs the user file in GLOBAL scope (not inside a function) precisely because user configs define functions/aliases; it fixes ZDOTDIR around the source, CAPTURES a user-side ZDOTDIR change as the new original directory, and restores the hijack dir to continue the chain. After .zshrc the hijack ENDS: real ZDOTDIR restored/unset so zsh natively reads the remaining login file (.zlogin). Then zsh-integration.zsh loads, whose one-shot precmd hook was appended LAST (comment: control over PS1 even if other hooks modify it). Debug tracing gated by JETBRAINS_INTELLIJ_TERMINAL_DEBUG_LOG_LEVEL using the (%):- %x expansion to print the executing filename.
**Invariant:** every user file runs EXACTLY ONCE, in zsh's native order, from its REAL location, with ZDOTDIR appearing natural during its execution; HISTFILE must be corrected before user .zshrc because etc/zshrc already miscomputed it. Recursion guard compares ZDOTDIR against the original dir, not just presence of the flag.
**Probe:** zsh is NOT installed on this host (command -v zsh failed) - the runtime smoke test is BLOCKED per missing-runner rule; verification rests on whole-file reads of all four files plus the documented order comment block (:9-19). Syntax-level runner likewise unavailable for zsh -n.
**Coverage caveat:** zdotdir dotfiles were parse_partial in index_status (leading-dot names); read directly as instructed there.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-phpstorm", query: "MATCH (f:File) WHERE f.file_path CONTAINS 'zdotdir' RETURN f.file_path ORDER BY path" });
```

## Verdict
Adopt the counterpart-sourcing ladder for ANY embedder-of-zsh (dev containers, terminals, agents). Adapt variable prefixes to your namespace; keep global-scope sourcing and the capture-back of user ZDOTDIR changes. Omit naive 'source ~/.zshrc at the end' designs - they break users who rely on ZDOTDIR-dependent configs.