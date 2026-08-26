<!-- capsule-v2 -->
# Env-force variables — how do you pass environment overrides INTO a shell that will re-read user rcfiles which might clobber them?

**Source:** JetBrains MPS install `MPS-261.25134.779`; `bash/bash-integration.bash:53-70` + `fish/fish-integration.fish:8-30`; Codebase Memory project `jetbrains-mps`. **Question:** what encoding lets one flat environment carry set/prepend instructions that survive rcfile rewrites?

## Connected graph-selected seam: override_jb_variables pair
**Path/Symbol:** `override_jb_variables` in bash-integration.bash:53-70 and fish-integration.fish:8-30.
**Signature:** scan `env` output; name prefix `_INTELLIJ_FORCE_SET_` (len 20) or `_INTELLIJ_FORCE_PREPEND_` (len 24); strip prefix; export under the real name.
**Data Shape:** instruction encoded IN THE VARIABLE NAME; value is the payload; prepend callers embed separators themselves (verified below).

### Decisive source (bash side)
```bash
if [[ $NAME = _INTELLIJ_FORCE_SET_* ]]; then
  NEW_NAME=${NAME:20}            # drop "_INTELLIJ_FORCE_SET_"
  export "$NEW_NAME"="$VALUE"
fi
if [[ $NAME = _INTELLIJ_FORCE_PREPEND_* ]]; then
  NEW_NAME=${NAME:24}
  export "$NEW_NAME"="$VALUE${!NEW_NAME}"   # indirect expansion: value+old, NO separator
fi
```

**Flow:** IDE exports e.g. `_INTELLIJ_FORCE_PREPEND_PATH=/opt/bin:` -> spawned shell replays rcfiles -> integration script walks `env` and applies instructions AFTER user config, so user PATH edits cannot erase the injected entries.
**Invariant:** prepend concatenation has NO separator — caller supplies trailing colon (P10 executed: inner PATH=/usr/bin + payload `/opt/x:/usr/bin` -> `/opt/x:/usr/bin/usr/bin`; SET variant landed verbatim). Offsets are prefix lengths: bash `${NAME:20}/${NAME:24}` (0-based) equals fish `string sub -s 21/-s 25` (1-based). Fish additionally splits PATH/CDPATH/MANPATH on ":" into LISTS (fish arrays need it); bash treats everything as strings.
**Probe (executed):** `env -i _INTELLIJ_FORCE_PREPEND_PATH=/opt/x:/usr/bin PATH=/usr/bin _INTELLIJ_FORCE_SET_FOO=bar HOME=/tmp/none bash --noprofile --norc -c "source .../bash-integration.bash >/dev/null 2>&1; echo PATH=$PATH FOO=$FOO"` -> `PATH=/opt/x:/usr/bin/usr/bin FOO=bar` GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-mps", query: "override_jb_variables force set prepend", limit: 5 });
// seam family lives inside bash-integration.bash / fish-integration.fish script sections
```

**Relationship:** `shell-env-promotion-force-vars.md` (PhpStorm source) covers the launcher-leak-prevention question; this MPS-source capsule pins the applied-after-rc semantics with a live prepend probe and the cross-shell offset equivalence.

**Coverage:** both files `no_recorded_issue`; probe executed byte-exact this pass.

## Verdict
Adopt: name-encoded instructions in a flat env for late-binding overrides that must beat rcfiles; apply them AFTER user config in your injection ladder. Adapt: prefixes/offset table to your brand; keep the no-separator prepend contract explicit or porters WILL double-colon. Omit: nothing else — the pattern is complete in ~18 lines.
