<!-- capsule-v2 -->
# Hashline format + recovery — content tags and anchor-proved replay

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi` (code-grounded, reactors read). **Path:** `packages/hashline/src/format.ts`, `recovery.ts`.

## Format: a compact, content-anchored patch grammar
**Path/Symbol:** `format.ts:formatReplaceHeader` (57), `formatCutHeader` (62), `formatInsertHeader` (81), `formatHashlineHeader` (133), `computeFileHash` (117–121), `splitAddressableFileLines` (146–152).
**Signature:** `computeFileHash(text): string`; `formatCutHeader(start, end = start): string`; `splitAddressableFileLines(text): string[]`.
**Data Shape:** a hashline document is a series of `[path#TAG]` file sections; `PUT` owns literal `+`/bare body rows, `CUT N.=M` deletes and optionally captures spans, `REM`/`MV` are file-level headers; `<N`/`>N`/`>$` are gap or tail locators; tags are four uppercase hex characters.

### Decisive source
```ts
export function computeFileHash(text: string): string {
  const normalized = normalizeFileHashText(text);
  const low16 = Bun.hash.xxHash32(normalized, 0) & 0xffff;
  return low16.toString(16).padStart(HL_FILE_HASH_LENGTH, "0").toUpperCase();
}
```

**Flow:** formatters write canonical headers; the parser accepts legacy separators and warns (never crashes) when auto-prefixing bare payload rows; hashing normalizes trailing whitespace (`normalizeFileHashText`) so an unchanged logical file keeps its tag; splitting removes one terminal-newline sentinel but preserves a deliberate terminal blank line.

**Invariant:** an empty `PUT` span degenerates to a delete while an empty gap insert is invalid; a clone short tag detects stale content but alone cannot prove a divergent file is safe to replay — that proof is Recovery's job.

**Probe:** `test/format-v2.test.ts` covers replacement, deletes, gaps, legacy separators, empty bodies, and terminal-newline addressing.

## Recovery: replay only anchor-proved edits
**Path/Symbol:** `recovery.ts:Recovery.tryRecover` (347–356); helpers `buildLineMap` (64), `validateRemappedAnchorContext` (162), `replayRemappedAnchorsOnCurrent` (305).
**Signature:** `new Recovery(store: SnapshotStore)`; `tryRecover(args: RecoveryArgs): RecoveryResult | null`.
**Data Shape:** `RecoveryArgs { path, currentText, fileHash, edits, clipboard? }`; `RecoveryResult { text, firstChangedLine?, warnings? }`. The snapshot store retains one-or-more texts per tag, including colliders.

### Decisive source
```ts
tryRecover(args: RecoveryArgs): RecoveryResult | null {
  // When retained texts collide on the 16-bit tag, use the latest one.
  // Recovery still requires its anchors and context to map unambiguously.
  const snapshot = this.store.byHash(path, fileHash);
  if (!snapshot) return null;
  return replayRemappedAnchorsOnCurrent(snapshot.text, currentText, edits, recoveryWarning, clipboard, path);
}
// deeper:
const lineMap = buildLineMap(previousText, currentText);
if (!validateRemappedAnchorContext(previousText, currentText, lineMap, edits)) return null;
return replayRemappedAnchorsOnCurrent(...);
```

**Flow:** recovery resolves the retained snapshot for the stale tag (latest on collisions, with an external-edit vs session-chain warning flavor), diffs previous → current to build a line map, proves each changed/duplicate/moved anchor against its neighbor context, then replays resolved edits on `currentText`. Failed or ambiguous proof returns `null`, leaving the caller to surface current context instead of editing a divergent file. (Legacy name `recover` is now `tryRecover` at HEAD.)

**Invariant:** independent live edits survive; changed, split, deleted, or ambiguous anchors are never guessed across. The proof window is bounded by the snapshots the store actually retains.

**Probe:** `test/recovery-session-chain.test.ts` proves anchor divergence, remap, duplicate-anchor rejection, and collision selection; `test/format-v2.test.ts` pins grammar.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(computeFileHash|Recovery|tryRecover|buildLineMap|validateRemappedAnchorContext)$", limit: 6, fields: ["signature"] });
```

## Verdict
Adopt content-derived short tags as staleness detectors, trailing-whitespace-normalized hashing, and null-on-unprovable anchor remap recovery; adapt the hash function (xxHash32/Bun) and tag width to host; omit collision-tolerant multi-snapshot retention if snapshots are content-addressed in the host. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk files.
