<!-- capsule-v2 -->
# Hashline normalize + prefix seams — shape round-trip, echoed-input stripping

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/hashline/src/normalize.ts`, `prefixes.ts`. **Question:** How does a patch engine stay byte-honest across CRLF/BOM files and never mistake an echoed `read` output for authored edits?

## Text-shape canonicalization (BOM + line endings)
**Path/Symbol:** `normalize.ts:detectLineEnding` (10–17), `normalizeToLF` (19–21), `restoreLineEndings` (24–26), `stripBom` (36–38).
**Signature:** `detectLineEnding(content): "\r\n" | "\n"` (first-ending wins, LF when neither); `normalizeToLF(text): string`; `restoreLineEndings(text, ending): string`; `stripBom(content): BomResult` with `{ bom, text }`.
**Data Shape:** strings + `LineEnding` union; BOM stripped once at the front, kept for write-back.

### Decisive source
```ts
export function detectLineEnding(content: string): LineEnding {
  const crlfIdx = content.indexOf("\r\n");
  const lfIdx = content.indexOf("\n");
  if (lfIdx === -1) return "\n";
  if (crlfIdx === -1) return "\n";
  return crlfIdx < lfIdx ? "\r\n" : "\n";
}
export function normalizeToLF(text: string): string { return text.replace(/\r\n?/g, "\n"); }
export function stripBom(content: string): BomResult {
  return content.startsWith("\uFEFF") ? { bom: "\uFEFF", text: content.slice(1) } : { bom: "", text: content };
}
```

**Flow:** before applying edits, content is BOM-stripped and normalized to LF so line anchors are stable; the detected `LineEnding` and BOM re-apply exactly on write-back so a CRLF file stays CRLF and a BOMed file keeps its BOM through patch + write. Patch math happens entirely in LF-space. (`\r\n?` also collapses bare-CR legacy files.)

**Invariant:** write-back restores the original shape, not the patcher's shape; BOM is resolved at capture time, never inferred at write time.

## Echoed-prefix stripping (read output → patch input), pre-tokenizer
**Path/Symbol:** `prefixes.ts:stripNewLinePrefixes` (99–123), `stripHashlinePrefixes` (129+); regexes `HL_PREFIX_RE` (19), `HL_HEADER_RE`, `DIFF_PLUS_RE` (22).
**Signature:** `stripNewLinePrefixes(lines: string[]): string[]` (opportunistic); `stripHashlinePrefixes(lines: string[]): string[]` (strict — every content line must be hashline-prefixed).
**Data Shape:** operates on line arrays; a stats pass (`collectLinePrefixStats`) counts non-empty lines, headers, hashline prefixes, diff-plus lines, and their overlap to decide strip mode; reader elision/metadata lines are recognized and filtered.

### Decisive source
```ts
const HL_PREFIX_RE = /^\s*(?:>>>|>>)?\s*(?:[+*-]\s*)?\d+[:|]/;
const DIFF_PLUS_RE = /^[+](?![+])/;
// opportunistic decision:
const stripHash = contentLineCount > 0 && stats.hashPrefixCount === contentLineCount;
const stripPlus =
  !stripHash &&
  stats.diffPlusHashPrefixCount === 0 &&
  stats.diffPlusCount > 0 &&
  stats.diffPlusCount >= stats.nonEmpty * 0.5;
```

**Flow:** runs *before* the tokenizer — a model echoing `read`/`search` output as a patch emits `123:`/`123|` numbered lines (hashline mode) or `+` diff echoes (non-hashline). The opportunistic variant strips hash prefixes when ALL content lines carry them, strips diff-plus only when ≥50% of non-empty lines are pure plus-prefixes with no mixed hashline-plus forms, handles the mixed `+42:` shape by stripping the numbered part, and leaves plain text untouched otherwise. Strict strips only when every content line is numbered. Truncated echoes carrying read-elision notices never become malformed ops.

**Invariant:** stripping is deterministic and idempotent — un-echoed text loses nothing; no stray echoed line prefix becomes a fake op.

**Probe:** `test/core-contracts.test.ts`, `test/leniency.test.ts`, `test/format-v2.test.ts`, `test/clipboard.test.ts`, `test/boundary-repair.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(detectLineEnding|restoreLineEndings|stripBom|stripNewLinePrefixes|stripHashlinePrefixes)$", limit: 8, fields: ["signature"] });
```

## Verdict
Adopt LF-space patch math with exact shape restoration on write-back, and stats-gated echo stripping that runs strictly before tokenization; adapt the prefix alphabet and elision markers to host readers; omit markdown-quote (`>>>`) handling unless the host renders reads as quotes. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk files.
