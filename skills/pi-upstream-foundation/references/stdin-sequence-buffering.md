<!-- capsule-v2 -->
# Stdin sequence buffering — how do you parse terminal input when escape sequences arrive split across chunks?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter reads raw stdin chunks and sees fragments become phantom keypresses — how does pi reassemble complete sequences?

## Per-protocol completeness classifiers, not one heuristic
**Path/Symbol:** `packages/tui/src/stdin-buffer.ts` (444L; WezTerm case :210-233, Kitty echo dedup field :288, classifier dispatch throughout).
**Signature:** internal buffer consumes chunks → emits only COMPLETE sequences (plus timed flushes).
**Data Shape:** Completeness is classified PER PROTOCOL: CSI ends on final byte 0x40-0x7E; OSC ends on ST or BEL; DCS/APC end on ST; SS3 is ESC + exactly one char; old-style mouse is a fixed 6 bytes.

### Decisive source
```ts
// WezTerm with enable_kitty_keyboard sends the Escape key PRESS as a raw
// \x1b byte and the RELEASE as a full Kitty CSI-u sequence, concatenated:
//   \x1b\x1b[27;...u
// A generic parser reads \x1b\x1b as meta-key and leaks the rest as text.
// Fix: when the char after \x1b\x1b begins ANY protocol starter ([ ] O P _),
// emit ONE Escape and restart parsing from the second byte.
```

**Flow:** chunk arrives → append to buffer → try to classify a complete sequence by protocol rules → emit it → keep partial tails buffered. Two TIME windows resolve ambiguities timing alone can't: ~50ms for incomplete sequences, ~10ms for a lone ESC (Escape key vs Alt+pending-key), tunable upward for high-latency SSH. Kitty protocol echo dedup (`pendingKittyPrintableCodepoint`) suppresses the printable-codepoint DUPLICATE the protocol produces. Bracketed paste is routed as ONE paste EVENT so multi-line pastes never execute line-by-line.
**Invariant:** No fragment of a multi-byte sequence may ever surface as keystrokes; each ambiguity class (incomplete vs lone-ESC vs protocol-echo) gets its own resolution mechanism rather than sharing one timeout.
**Probe:** `packages/tui/test/stdin-buffer.test.ts` (protocol-specific fixture suites driving StdinBuffer directly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "StdinBuffer kitty wezterm escape", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-protocol completeness classification + dual timing windows + paste-as-event. Adapt window durations to your latency envelope. Omit protocols your targets don't emit. Coverage caveat: none.
