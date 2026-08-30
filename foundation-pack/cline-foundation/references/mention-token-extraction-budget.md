<!-- capsule-v2 -->
# mention-token-extraction-budget — how do you turn @path tokens into budgeted matched-file lists WITHOUT mutating the prompt?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How should an @-mention enricher partition tokens into matched vs ignored under byte budgets while leaving user input untouched?

## Whitespace-anchored extraction; linear punctuation trim; budget ladder that charges the CAP, not the file size
**Path/Symbol:** `sdk/packages/core/src/services/workspace/mention-enricher.ts` (`enrichPromptWithMentions` :63-130; `extractMentionTokens` :29-46; `normalizeMentionPath` :48-61; `stripTrailingPunctuation` :21-27).
**Signature:** `enrichPromptWithMentions(input, cwd, {ttlMs?, maxFiles?, maxFileBytes?, maxTotalBytes?}?): Promise<{prompt, mentions[], matchedFiles[], ignoredMentions[]}>`.
**Data Shape:** Result partitions every extracted mention into matchedFiles or ignoredMentions; `prompt` is returned UNCHANGED in every path (enrichment is a side list, never a rewrite). Extraction regex `(^|[\s])@([^\s]+)` — start-of-input or whitespace-preceded only.

### Decisive source
```ts
// DEAD-KNOB FINDING (verified this pass at pin): attachments is declared and
// NEVER appended, so attachments.length === 0 forever and the maxFiles gate
// can NEVER fire — both the array and the cutoff are unreachable code.
const attachments: Array<{ path: string; content: string }> = [];
for (const mention of mentions) {
	if (maxFiles && attachments.length >= maxFiles) { ignored.push(mention); continue; }  // dead
	...
	if (!maxFileBytes || !maxTotalBytes) { matched.push(relativePath); continue; } // EITHER cap unset ⇒ NO size checks
	const fileStat = await stat(absolutePath);
	if (!fileStat.isFile()) { ignored.push(mention); continue; }
	const nextBytes = totalBytes + maxFileBytes;   // charges the CAP CONSTANT, not stat.size
	if (nextBytes > maxTotalBytes) { ignored.push(mention); continue; }
	totalBytes = nextBytes; matched.push(relativePath);
}
```

**Flow:** extract (whitespace-anchored ⇒ emails like `test@example.com` never match; strip leading wrappers `[(`'"]+`; LINEAR trailing-punctuation scan over `),.:;!?`'\"` — regression-pinned against catastrophic backtracking with a 25k `!` run; drop tokens still containing `@`; Set-dedupe) ⇒ zero mentions ⇒ identity result ⇒ else fetch `getFileIndex(cwd)` ⇒ per mention: dead maxFiles gate → normalize to workspace-relative POSIX (`..`/absolute/outside-root ⇒ ignored) → index-membership check → optional size ladder above.
**Invariant:** The enricher never rewrites user input and never throws per-file (stat errors ⇒ ignored); when budgets apply, admission cost is predictable (count × maxFileBytes ≤ maxTotalBytes) rather than content-dependent.
**Probe:** `grep -cF 'const nextBytes = totalBytes + maxFileBytes;' sdk/packages/core/src/services/workspace/mention-enricher.ts` → 1 (:111). Test pins (`mention-enricher.test.ts`, 5 cases read whole): "ignores emails and unmatched mentions", "strips trailing punctuation without backtracking" (:65), "respects maxTotalBytes while keeping prompt unchanged", "does not over-count totalBytes across multiple mentions" (3×5=15≤15 all matched). NOTE: no test exercises a maxFiles overflow — consistent with the gate being dead.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.services.workspace.mention-enricher.enrichPromptWithMentions" });
// observed: Function lines 63-130 verbatim, byte-equal to the checkout whole-read
```

## Verdict
Adopt whitespace-anchored token extraction with linear punctuation trimming, membership-gated matching against a file index, and prompt-immutability. RE-DERIVE any maxFiles semantics before porting — at this pin the cutoff is unreachable dead code; if you need a count cap, count `matched.length` instead. Adapt budgets to real file sizes if content-dependent admission is desired. Coverage caveat: `mention-enricher.test.ts:9` parse_partial flag is the type-only mock-import argument, read directly (:7–16); no dedicated suite for the dead-knob behavior. Runner-BLOCKED honestly (no node_modules).
