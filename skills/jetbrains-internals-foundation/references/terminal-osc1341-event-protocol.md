<!-- capsule-v2 -->
# OSC-1341 verification harness & latent-bug delta — how do you PROVE an OSC-1341 terminal integration works, and which shipped fallback must never be ported?

**Source:** JetBrains MPS install `MPS-261.25134.779` (proprietary distribution; scripts headered Apache-2.0), root `/mnt/hdd/utopia/inspo/mps`; Codebase Memory project `jetbrains-mps` (1,245 nodes). **Question:** given the wire format (owned by `terminal-osc1341-command-block-protocol.md`), what deterministic probe battery pins a correct implementation, and where does the SHIPPED code itself deviate from its own spec?

## Relationship to the base-protocol capsule
This is the MPS-source DELTA companion to `terminal-osc1341-command-block-protocol.md` (PhpStorm source): that capsule owns the frame grammar/event census/hook-strategy survey. This capsule adds what only live execution can prove: byte-level framing, encoder round-trips incl. non-ASCII, gate switching, JSON escaping — plus a probe-confirmed LATENT BUG in the shipped bash fallback.

## Connected graph-selected seam: encode family under live execution
**Path/Symbol:** `plugins/terminal/shell-integrations/bash/command-block-support.bash:37` `__jetbrains_intellij_encode`; fallback `__jetbrains_intellij_encode_slow` :22-34; `escape_json` :83-87; graph snippet retrieval returned :37-44 byte-identical to disk (callers=5).
**Signature:** `encode <s> -> hex(UTF-8 bytes)`; fast path `od -An -tx1 -v | tr -d "[:space:]"` when od+tr exist, else char-loop fallback.
**Data Shape:** out = uppercase two-digit hex/byte, no separators; frames terminate BEL 0x07 (NOT ST).

### Decisive source (the broken fallback)
```bash
__jetbrains_intellij_encode_slow() {
  local out=''
  builtin local i hexch LC_CTYPE=C LC_COLLATE=C LC_ALL= LANG=
  builtin local value="$1"
  for ((i = 1; i <= ${#value}; ++i)); do
    builtin printf -v hexch "%02X" "'$value[i]"   # BUG: $value[i] does not subscript scalars in bash
    out+="$hexch"
  done
  builtin printf "%s" "$out"
}
```

**Flow:** emitters assume fallback == fast path; in bash the fallback expands `$value[i]` as `$value` + literal `[i]`, so `%02X` always reads the FIRST character after the leading quote -> output = first-char hex repeated ${#value} times.
**Invariant (the finding):** the two paths are NOT equivalent in bash. Minimal repro (P7b, executed): `value=héllo; printf "[%s]\n" "$value[i]"` prints `[héllo[i]]`. Full-function effect (P5b, executed against the SHIPPED file): `__jetbrains_intellij_encode_slow héllo` -> `686868686868`, while the fast path returns correct `68c3a96c6c6f` (P5c). Harmless in practice only because od/tr are effectively universal; the identical loop IS correct in the zsh twin because zsh subscript-expands `$var[i]` natively (zsh runner absent on host — read-verified only). PORT THE FAST PATH; delete or fix the fallback.
**Probe (executed battery, all GREEN):**
- P1 hex fast path: `printf %s abc | od -An -tx1 -v | tr -d "[:space:]"` -> `616263`.
- P1b non-ASCII: input `héllo` -> `68c3a96c6c6f` (UTF-8 bytes, é=c3a9).
- P2 frame bytes: `printf "\e]1341;command_finished;exit_code=%s\a" 0 | od -c` -> `033 ] 1341 ; ... = 0 \a` (ESC/BEL framing pinned).
- P3/P3b gate switch: sourcing classic .bash WITHOUT `INTELLIJ_TERMINAL_COMMAND_BLOCKS` defines NO `__jetbrains_*` functions, exit 0; WITH it `type -t __jetbrains_intellij_command_terminated` -> `function`. (bind -x warns "line editing not enabled" non-interactively — graceful.)
- P4 escape_json: `a "quote" back\slash` -> `a \"quote\" back\\slash` (backslash doubled BEFORE quote escaping — order matters).
- P12 clear override: `clear` emits exactly `ESC ]1341;clear_invoked BEL`, no ANSI clear sequence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-mps", qualified_name: "jetbrains-mps.plugins.terminal.shell-integrations.bash.command-block-support.__jetbrains_intellij_encode" });
// executed this pass: lines 37-44 byte-match disk; callers=5 callees=1
// search_graph "encode escape json": total=13 hits across bash/zsh/fish x classic/reworked
```

**Coverage:** cited .bash/.zsh/.fish paths `no_recorded_issue` (check_index_coverage executed); ps1 scripts are UTF-16LE CRLF — grep-blind, read via iconv decode; zsh/fish/pwsh runtimes unavailable on host, their claims stay read+graph evidence (same block recorded by the base capsule).

## Verdict
Adopt: this five-probe battery (framing bytes / ASCII / non-ASCII / gate / json-escape) as the minimum acceptance harness for any OSC-style integration port. Adapt: expected digests to your event set. Omit: the bash char-loop fallback pattern entirely — copy the zsh form if you need an od-less path.
