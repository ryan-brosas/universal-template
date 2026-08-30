<!-- capsule-v2 -->
# PS destructive-command warnings — how do you add informational danger hints WITHOUT touching permission logic?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do regex warning detectors coexist with an AST permission engine without either duplicating or weakening it?

## Statement-anchored flag-order patterns; UI-only channel
**Path/Symbol:** `src/tools/PowerShellTool/destructiveCommandWarning.ts`:`DESTRUCTIVE_PATTERNS` (:12-96), `getDestructiveCommandWarning` (:102-109).
**Signature:** `function getDestructiveCommandWarning(command: string): string | null`.
**Data Shape:** Ordered `{ pattern: RegExp, warning: string }[]`; first match wins (Recurse+Force before bare-Recurse before bare-Force so the strongest wording shows).

### Decisive source
```ts
// Anchored to statement start (^, |, ;, &, newline, {, () so `git rm --force`
// doesn't match — \\b would match `rm` after any word boundary. The `{(`
// chars catch scriptblock/group bodies ... The stopper adds only `}` (NOT `)`)
// — `}` ends a block so flags after it belong to a different statement ..., but
// `)` closes a path grouping and flags after it are still this command's flags:
// `Remove-Item (Join-Path $r "tmp") -Recurse -Force` must still warn.
/(?:^|[|;&\n({])\s*(Remove-Item|rm|del|rd|rmdir|ri)\b[^|;&\n}]*-Recurse\b[^|;&\n}]*-Force\b/i
```

**Flow:** pure string test over the raw command → returns a human warning for the dialog ("may recursively force-remove files", git reset --hard/push --force/clean -f, Format-Volume/Clear-Disk, DROP/TRUNCATE, Stop/Restart-Computer, Clear-RecycleBin).
**Invariant:** Explicitly non-authoritative — "purely informational -- it doesn't affect permission logic or auto-approval." The character-class grammar (`[^|;&\n}]*` with `)` deliberately NOT a stopper) is the subtle part a naive port gets wrong in both directions.
**Probe:** `grep -nF "purely informational" src/tools/PowerShellTool/destructiveCommandWarning.ts` → :3 and `grep -cF "warning: 'Note:" src/tools/PowerShellTool/destructiveCommandWarning.ts` → `15` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getDestructiveCommandWarning DESTRUCTIVE_PATTERNS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the separation (warnings inform prompts; never gate) and both anchor subtleties. Adapt the pattern list to your shell. Omit git-pattern duplication notes vs BashTool. Coverage caveat: probes deterministic; no upstream tests.
