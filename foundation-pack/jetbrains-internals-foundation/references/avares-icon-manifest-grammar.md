<!-- capsule-v2 -->
# avares:// icon resource manifest — what does the profiler's list.txt inventory and why does it carry IDE icons?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** How are embedded Avalonia resources inventoried, and what naming grammar keeps light/dark/state variants resolvable?

## list.txt avares URI census + variant suffix grammar
**Path/Symbol:** `list.txt` (7,093 lines, root) — EVERY line is `avares://JetBrains.Avalonia.IntelliJIcons/…`; sibling `hash.txt` holds one sha256 `41e6f64…` (install self-hash pairing). Same `_dark` contract as the leaf's icon-library-migration-map, now inside a .NET/Avalonia resource assembly.
**Signature:** `avares://<ResourceAssembly>/<path-including-state-suffixes>.svg` where suffixes observed = `_dark` (2,437), `(Color)` (186), `(Gray)` (184), `(GrayDark)` (184).
**Data Shape:** one assembly packages the IntelliJ IDE icon tree (idea/plugins/... incl. llm agent icons claudeCloud/codexCloud/gemini/junieCloud/agent-model) so a standalone tool renders IDENTICAL iconography to the IDEs; the text manifest enumerates the whole keyspace.

### Decisive source
```text
$ head -3 list.txt
avares://JetBrains.Avalonia.IntelliJIcons/idea/plugins/llm/agents/acp/resources/icons/agent-model.svg
avares://JetBrains.Avalonia.IntelliJIcons/idea/plugins/llm/agents/acp/resources/icons/agent-model_dark.svg
avares://JetBrains.Avalonia.IntelliJIcons/idea/plugins/llm/agents/acp/resources/icons/claudeCloud.svg
$ tail -1 list.txt
avares://JetBrains.Avalonia.IntelliJIcons/net/UnitTesting/UnitTestRunner(GrayDark).svg
$ sed -E 's|^avares://([^/]+)/.*|\1|' list.txt | sort -u   →   JetBrains.Avalonia.IntelliJIcons
```

**Flow:** icons compiled INTO an Avalonia resource assembly -> runtime resolves by avares:// key -> state/darkness chosen by suffix lookup; list.txt acts as the offline inventory enabling existence checks and integrity pairing with hash.txt.
**Invariant:** darkness is a NAMING suffix (`_dark`), emphasis is a parenthesized state suffix family — resolvers must try suffixed keys before failing, and any icon addition must extend the manifest or offline consumers drift.
**Probe:** `grep -c '_dark' list.txt` → 2437; `grep -c '(Gray)' list.txt` → 184; single-assembly sed census → exactly one key (all executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "Avalonia GUI resources icons", limit: 5 });
```
Caveat: SVG payloads are binary-excluded; the indexed plane is the doc-comment XML of consumer assemblies.

## Verdict
Adopt assembly-embedded icon resources keyed by suffixed avares-style URIs plus a shipped plaintext inventory; adapt suffix vocabulary to your theme system; omit the IDE-icon reuse if your tool has no sibling IDE to stay visually identical with.
