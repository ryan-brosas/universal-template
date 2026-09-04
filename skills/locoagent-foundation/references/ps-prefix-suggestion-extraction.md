<!-- capsule-v2 -->
# PS prefix suggestion extraction — how do you propose a "don't ask again for ___" rule that can never over-allow?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How does the permission dialog derive a static command prefix from a parsed PowerShell element, and which five failure modes must each refuse to suggest rather than guess?

## extractPrefixFromElement refusal ladder + positional word-integrity walk
**Path/Symbol:** `src/utils/powershell/staticPrefix.ts`:`extractPrefixFromElement` (:30-156), `getCommandPrefixStatic` (:166-186), `getCompoundCommandPrefixesStatic` (:204-284), `wordAlignedLCP` (:294-316); inputs from `dangerousCmdlets.ts`:`NEVER_SUGGEST` (:158-185 — union of all validator cmdlet sets + shells + cross-platform code-exec, alias-expanded).
**Signature:** `async function getCommandPrefixStatic(command: string): Promise<{ commandPrefix: string | null } | null>`; `getCompoundCommandPrefixesStatic(command, excludeSubcommand?): Promise<string[]>`.
**Data Shape:** Suggested rules are `PowerShell(<prefix>:*)`; prefixes are space-joined words.

### Decisive source
```ts
// Post-buildPrefix word integrity: buildPrefix space-joins consumed args ...
// git 'push origin' → args=['push origin']. If that arg is consumed,
// buildPrefix emits 'git push origin' — silently promoting 1 argv element to
// 3 prefix words. Rule PowerShell(git push origin:*) then matches
// `git push origin --force` ... The old set-membership check was defeated
// by decoy args: `git 'push origin' push origin` → each word ∈ args → passed.
// Now POSITIONAL: walk args in order; each prefix word must exactly match the
// next non-flag arg.
```

**Flow:** refusals: application names (path-run files), NEVER_SUGGEST members (wildcard rules on them would bypass callbacks forever via prefix-startsWith — e.g. accepting `ForEach-Object:*` at a callback-rejection moment auto-allows future scriptblocks), non-literal name elementTypes[0] (`& $cmd status`), any dynamic arg elementType. For externals: fig-spec-driven buildPrefix (shared with bash) with depth rules so bare `gcloud:*` never forms; then positional word-integrity walk (flags skipped only when the spec says they take values); then bare-root guard (single-word result refused when spec declares subcommands). Compound: root-grouped case-insensitive word-aligned LCP collapse, but a group collapsing to a subcommand-aware single word is DROPPED entirely.
**Invariant:** A suggested rule is a PROMISE the engine will auto-allow later inputs; every ambiguity must shrink the suggestion (null) rather than broaden it. NEVER_SUGGEST is derived FROM the validator lists so adding a cmdlet to security automatically removes it from suggestions — no second list to sync.
**Probe:** `grep -nF "NEVER_SUGGEST" src/utils/powershell/staticPrefix.ts | head -2` and `grep -nF "function wordAlignedLCP" src/utils/powershell/staticPrefix.ts` and `grep -cF "return null" src/utils/powershell/staticPrefix.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "extractPrefixFromElement buildPrefix NEVER_SUGGEST", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves parser-plane symbols incl. getAllCommands used by the extractor)*

## Verdict
Adopt derive-don't-duplicate suggestion blocklists and the refusal-over-guess ladder. Adapt spec registry to your CLI corpus. Omit bash-parity notes beyond shared-buildPrefix fact. Coverage caveat: probes deterministic; no upstream tests.
