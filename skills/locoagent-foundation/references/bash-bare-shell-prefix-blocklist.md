<!-- capsule-v2 -->
# Bare shell prefix blocklist — never suggest what approximates Bash(*)

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which prefixes must a permission-suggestion engine refuse to generate because they'd auto-approve arbitrary code?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashPermissions.ts` — `BARE_SHELL_PREFIXES` (:196-227), consulted by `getFirstWordPrefix` (:243-283) and implicitly by `suggestionForExactCommand` via `getSimpleCommandPrefix`; mirror note: `DANGEROUS_SHELL_PREFIXES` in `src/utils/shell/prefix.ts` guarded the old Haiku extractor.
**Signature:** `getFirstWordPrefix(command) → string | null` — returns null (no suggestion) for blocked names.
**Data Shape:** Set of bare command names: sh/bash/zsh/fish/csh/tcsh/ksh/dash/cmd/powershell/pwsh + env/xargs + nice/stdbuf/nohup/timeout/time + sudo/doas/pkexec.

### Decisive source
```ts
// SECURITY: checkSemantics (ast.ts) strips these wrappers to check the
// wrapped command. Suggesting `Bash(nice:*)` would be ≈ `Bash(*)` — users
// would add it after a prompt, then `nice rm -rf /` passes semantics while
// deny/cd+git gates see 'nice' (SAFE_WRAPPER_PATTERNS below didn't strip
// bare `nice` until this fix). Block these from ever being suggested.
```

**Flow:** when the UI needs an editable prefix suggestion for a prompt, first-token extraction runs; if the token is a shell interpreter (`bash:*` allows `-c "anything"`), an exec-wrapper (`env:*`, `xargs:*`), a semantics-stripped wrapper (`nice:*` ≈ allow-everything because checks look through it while deny gates see the wrapper), or a privilege escalator (`sudo:*` auto-approves future sudo), the suggestion is refused rather than minted. UI-only fallback exists precisely because external builds lack tree-sitter refinement — without the blocklist the fallback would happily propose `Bash(bash:*)`.

**Invariant:** (1) A suggested rule is a persistent grant: any prefix that can carry an arbitrary payload (`-c`-style shells, argv-exec wrappers) or that your own checker STRIPS THROUGH is equivalent to allow-all and must never be generated. (2) The blocklist must track BOTH directions of wrapper asymmetry — if checkSemantics sees through `nice`, then suggesting `nice:*` grants everything while deny matching still sees 'nice' (the exact recorded incident). (3) Editable-in-UI is not a reason to soften: the same list backs backend suggestions. (4) Keep the mirror set in sync with whatever generates prefixes from model output.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'would be ≈' src/tools/BashTool/bashPermissions.ts` → :212; `grep -nF "'pkexec'," src/tools/BashTool/bashPermissions.ts`; `grep -nF 'DANGEROUS_SHELL_PREFIXES' src/utils/shell/prefix.ts`; graph resolves getFirstWordPrefix :243-283 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "BARE_SHELL_PREFIXES getFirstWordPrefix suggestionForExactCommand", limit: 5 });
```

## Verdict
Adopt as-is for any permission-prompt UX that proposes prefix rules from observed commands. The category boundaries (interpreter / exec-wrapper / stripped-through wrapper / privilege escalator) are the reusable content.
