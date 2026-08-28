<!-- capsule-v2 -->
# Instruction-context ambient source — how do you turn ambient repo instruction files into a reconcilable context source that survives partial filesystem failure?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A coding agent must load ambient AGENTS.md instructions (global + upward project walk) as system context that reconciles like any other source — but instruction files live on a filesystem that can race (a discovered file vanishing between discovery and read). How do you shape the source so partial failure degrades to "keep what was admitted" instead of dropping or duplicating instructions?

## One composite source for the whole ambient set
**Path/Symbol:** `packages/core/src/instruction-context.ts` (`key` :20, `source` :29-38, `observe` :40-74, `registry.register` :76-88, `render` :99-101).
**Signature:** `source(value: ReadonlyArray<File> | SystemContext.Unavailable) → SystemContext` where `File = { path: AbsolutePath, content: string }`; registered load: `observe().pipe(Effect.map(...), Effect.catch(...), Effect.catchDefect(...))`.
**Data Shape:** value is the WHOLE instruction set as one list — the compare ladder diffs it as a unit, never per-file. `update(previous, current)` returns a full-replace preamble + re-render; `removed()` returns the fixed sentence "Previously loaded instructions no longer apply."

### Decisive source
```ts
// instruction-context.ts:44-58 — boundary-gated upward discovery + fail-open availability
const insideProject =
  fromProject === "" || (fromProject !== ".." && !fromProject.startsWith(`..${sep}`) && !isAbsolute(fromProject))
const discovered = new Set(
  yield* Effect.forEach(
    Flag.OPENCODE_DISABLE_PROJECT_CONFIG || !insideProject
      ? []
      : yield* fs.up({ targets: ["AGENTS.md"], start, stop }),
    fs.resolve,
  ),
)
const paths = Array.dedupe([yield* fs.resolve(join(global.config, "AGENTS.md")), ...discovered])
...
if (files.some((file, index) => file === undefined && discovered.has(paths[index])))
  return SystemContext.unavailable
```

**Flow:** observe resolves start (working directory) and stop (project directory); the upward walk runs only when not disabled by flag AND the working directory is inside the project (relative-path escaping check). Discovered paths dedupe with the always-included global `<config>/AGENTS.md`; every path is read with `readFileStringSafe` (undefined = vanished). If ANY DISCOVERED path came back undefined, the whole source becomes `SystemContext.unavailable` — the compare ladder then returns Unchanged, keeping previously admitted instructions. An empty discovery set yields `SystemContext.empty` (no source at all, not an empty block); an empty FILE still renders (`Instructions from: <path>\n`). Registration wraps load in catch + catchDefect → `source(unavailable)`, so discovery errors never kill the registry load.
**Invariant:** fail-open for availability — a filesystem race must preserve admitted instructions (Unchanged), never emit a partial set that would silently drop instructions from the model's context; the global file alone missing is tolerated (filtered out) because it was not "discovered".
**Probe:** `packages/core/test/instruction-context.test.ts` (323L, 2 `it.live` + 5 `it.effect`): the first it.live pins baseline order (global, nearest-package, project), the Updated re-render after edit, the full-replace update text after partial removal, and the removed sentence after all files vanish; "preserves admitted instructions while observation is unavailable" (:140) pins failing-FS → Unchanged; "preserves admitted instructions when a discovered file disappears before read" (:175) pins racing-FS → Unchanged; "honors the project instruction opt-out" (:258) pins no scan under the flag; "does not discover project instructions outside the canonical project root" (:293) pins the boundary check. Source pin:
```bash
grep -c 'replace all previously loaded' packages/core/src/instruction-context.ts   # expect 1
grep -c 'no longer apply' packages/core/src/instruction-context.ts                 # expect 1
grep -c 'OPENCODE_DISABLE_PROJECT_CONFIG' packages/core/src/instruction-context.ts # expect 1
grep -c 'SystemContext.unavailable' packages/core/src/instruction-context.ts       # expect 4
grep -c 'SystemContext.empty' packages/core/src/instruction-context.ts             # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "InstructionContext observe AGENTS.md fs.up unavailable SystemContext registry core/instructions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole-set-as-one-source shape with full-replace update text and the fail-open-to-Unchanged availability rule for discovered files; adopt the boundary-gated walk (flag + project containment) and global-file dedupe. Adapt the File schema and render wording to your host; omit opencode's specific flag name. Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
