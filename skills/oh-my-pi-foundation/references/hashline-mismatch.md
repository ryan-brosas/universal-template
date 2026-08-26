<!-- capsule-v2 -->
# Hashline mismatch — what does a stale-read rejection tell the model to do next?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you reject an edit bound to stale file content while turning the refusal into a recovery instruction?

## Two-branch rejection taxonomy: drifted vs fabricated tags
**Path/Symbol:** `packages/hashline/src/mismatch.ts:MismatchError` (55–111), `rejectionHeader` (85–98), `parseTag` (23–31), `validateLineRef` (114–118).
**Signature:** `new MismatchError(details: MismatchDetails)`; `get displayMessage(): string`; `parseTag(ref): { line }`.
**Data Shape:** `MismatchDetails { path?, expectedFileHash, actualFileHash, fileLines, anchorLines?, hashRecognized? = true }` — hashes are 4-hex snapshot tags; `fileLines`+`anchorLines` feed `formatAnchoredContext` for the diagnostic body.

### Decisive source
```ts
if (!hashRecognized) {
  return [
    `Edit rejected${pathText}: hash #${expected} is not from this session.`,
    `The current file hashes to #${actual}. Re-read the file with \`read\` to copy a current [path#tag] header — never invent the tag and never reuse one from a prior session.`,
  ];
}
return [
  `Edit rejected${pathText}: file changed between read and edit.`,
  `Section is bound to #${expected}, but the current file hashes to #${actual}. If a prior edit in this session modified this file, copy the [path#newhash] header from that edit's response; otherwise re-read ... before retrying.`,
];
```

**Flow:** patcher compares section's snapshot tag against live content hash → mismatch raises `MismatchError` → message branches on `hashRecognized`: tag seen earlier THIS session ⇒ "copy the new hash from that edit's response" (cheapest correct retry); tag never recorded ⇒ "never invent the tag, re-read" (fabricated/carried-over case) → anchored context lines render below so the model can see what actually changed.
**Invariant:** a refusal is always actionable — it names both the expected and actual hash and the exact recovery move; disk is untouched on rejection (no partial write can accompany a mismatch).
**Probe:** direct `packages/hashline/test/patcher.test.ts:85` ("refuses with mismatch when the recorded version no longer matches live content" — asserts `/file changed between read and edit/` AND `fs.get(PATH)` still `"drifted\n"`); `:110` fabricated-tag branch asserting `"not from this session"` + `"never invent the tag"`; collision-trust rule at `:131` comment.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^MismatchError$", limit: 5, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.mismatch.MismatchError" });
```

## Verdict
Adopt the two-branch taxonomy (session-observed drift vs never-seen tag) with dual-hash actionable messages and anchored context; adapt wording/hash width to your read format; omit `formatAnchoredContext` details if your host has no numbered-line echo. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk test files.
