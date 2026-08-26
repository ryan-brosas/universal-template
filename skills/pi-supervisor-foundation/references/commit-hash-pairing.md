<!-- capsule-v2 -->
# Commit-hash pairing — pairing `git commit -m` calls with hashes recovered from following tool results

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you build an accurate "what was committed" section from conversation blocks alone?

## Message from args, hash from output
**Path/Symbol:** `src/compaction/extract/commits.ts:24-68` (`extractCommits`), formatting :70-78.
**Signature:** `extractCommits(blocks: NormalizedBlock[]): CommitInfo[]` where `CommitInfo = { hash?: string; message: string }`; `formatCommits(commits, limit=8)` keeps most recent.
**Data Shape:** Only `bash` tool_calls whose command matches `\bgit\s+commit\b`; message via `COMMIT_MSG_RE` handling double/single-quoted and shell-escaped forms; hash window = next **+3** blocks.

### Decisive source
```ts
    for (let j = i + 1; j < Math.min(blocks.length, i + 3); j++) {
      const r = blocks[j];
      if (r.kind !== 'tool_result') continue;
      // Common git commit output: `[branch <hash>] message` or `<branch> <hash>..<hash>`
      const bracket = r.text.match(/\[\S+\s+([0-9a-f]{7,12})\]/);
      if (bracket) { hash = bracket[1]; break; }
      const range = r.text.match(/\b([0-9a-f]{7,12})\.\.([0-9a-f]{7,12})\b/);
      if (range) { hash = range[2]; break; }        // push ranges: take the NEW head
      const plain = r.text.match(HASH_RE);
      if (plain) { hash = plain[1]; break; }
    }
```

**Flow:** find commit commands → parse first line of cleaned message (unescape `\"`/`\'`) → scan following results through the three-shape ladder (bracketed → push-range tail → bare 7–12 hex) → dedupe on `hash::message`.
**Invariant:** The three hash shapes are ordered most-specific-first; taking `range[2]` (the right side of `a..b`) encodes "after push, b is the new head". Dedupe key includes BOTH hash and message because amend flows reuse messages with new hashes. Unpaired commits keep `hash: undefined` and still render.
**Probe:** `grep -cF 'r.text.match(/\[\S+\s+([0-9a-f]{7,12})\]/)' src/compaction/extract/commits.ts` → 1; `grep -c "i + 3" src/compaction/extract/commits.ts` → 1. Direct-test caveat: no dedicated upstream test file for extractCommits — pinned by source read + byte-exact greps here (gate-3 caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "extractCommits|formatSummary|capBrief", limit: 10 });
```

## Verdict
Adopt arg-side message + result-side hash pairing with the three-shape specificity ladder for any git-aware summarizer. Adapt to your VCS's output shapes (add shapes rather than loosening HASH_RE). Omit nothing — the range-tail rule is what makes pushed-commit attribution correct.
