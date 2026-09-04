<!-- capsule-v2 -->
# Commit extraction — how are git commits harvested from tool calls and paired with their hashes?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Which command forms yield commit messages, how is the hash recovered from output, and what dedup key prevents duplicates?

## extractCommits + formatCommits (`src/compaction/extract/commits.ts`)
**Path/Symbol:** `src/compaction/extract/commits.ts:extractCommits` (:24-68), `formatCommits` (:70-78), regexes :8-11.
**Signature:** `(blocks) => CommitInfo[]`; `formatCommits(commits, limit=8) => string[]`.
**Data Shape:** `CommitInfo = {hash?: string /*7-12 hex*/, message: string}`; message = FIRST line of the `-m` payload.

### Decisive source
```ts
const COMMIT_MSG_RE = /git\s+commit[^\n]*?-m\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|\$?'((?:[^'\\]|\\.)*)')/;
// hash hunt in the NEXT 2 blocks' tool_results, three patterns in order:
const bracket = r.text.match(/\[\S+\s+([0-9a-f]{7,12})\]/);   // [branch abc1234] message
const range   = r.text.match(/\b([0-9a-f]{7,12})\.\.([0-9a-f]{7,12})\b/); // push output → take NEW hash
const plain   = r.text.match(HASH_RE);
// dedup by message+hash composite:
const key = `${hash ?? ''}::${message}`;
```

**Flow:** scan bash tool_calls for `git commit … -m "…"` (double/single/dollar-quoted variants; escaped chars tolerated inside quotes) → take first line of the unescaped message → look ahead ≤2 blocks for the result and try bracket → range → bare-hash patterns → dedup by `hash::message`. Formatting keeps the most recent 8 (`slice(-limit)`), prefixing `hash: ` when known.
**Invariant:** (1) The lookahead is bounded (≤2 blocks) like all pairing in this repo — distant outputs never misattach. (2) Range-form pushes deliberately take `range[2]` (the NEW hash). (3) Hash absence is fine — dedup still works via the empty-hash prefix. (4) Message cleaning handles `\"` and `\'` escapes BEFORE first-line split so embedded quotes don't truncate.
**Probe:** regex pins at commits.ts :8-11; behavior rides structured-sections suite `tests/full-fidelity-snapshot.test.ts` (:143+); graph pin resolves `extractCommits` line-exact via search_graph.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractCommits COMMIT_MSG_RE HASH_RE formatCommits", limit: 8 });
```

## Verdict
Adopt bounded-lookahead commit harvesting with the three-pattern hash ladder. Adapt to your shell-quoting conventions. Omit if your supervisor never sees shell commands.
