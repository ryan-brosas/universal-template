<!-- capsule-v2 -->
# Task-spec content-hash CAS file store — how do you let users hand-edit Markdown while the system overwrites it safely?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** what guards must wrap read-modify-write of a user-editable spec file so concurrent human edits are detected, not clobbered?

## `AgendaTaskSpecFileStore.writeSpec` / `assertExpectedContent` / path+symlink+containment guards
**Path/Symbol:** `sdk/packages/core/src/tasks/specs/task-spec-file-store.ts` — `writeSpec` :120-164, `assertExpectedContent` :195-213, `resolveSpecPath` :238-254, `assertSpecsDirSafe` :215-236, `readSpec` :106-118; hash in `sdk/packages/core/src/tasks/specs/task-spec-parser.ts:144-150`.
**Signature:** `writeSpec(input: AgendaTaskSpecWriteInput, options: WriteAgendaTaskSpecOptions = {}): WrittenAgendaTaskSpec` with options `{ specPath?, expectedContentHash?, createOnly? }`.

### Decisive source
```ts
const temporaryPath = join(this.specsDir,
    `.${basename(target)}.${process.pid}.${Date.now()}.tmp`);
try {
    writeFileSync(temporaryPath, raw, { encoding: "utf8", mode: 0o600 });
    this.assertExpectedContent(target, options);   // CAS check AFTER temp write, BEFORE publish
    if (options.createOnly) {
        linkSync(temporaryPath, target);           // atomic fail-if-exists create
    } else {
        renameSync(temporaryPath, target);
    }
} finally {
    if (existsSync(temporaryPath)) rmSync(temporaryPath, { force: true });
}
// assertExpectedContent (update path):
if (current.contentHash !== options.expectedContentHash) {
    throw new Error(`task spec changed before update: ${target}`);
}
```
```ts
// task-spec-parser.ts — what "content" means:
function hashContent(frontmatter: unknown, body: string): string {
    return createHash("sha256")
        .update(JSON.stringify(frontmatter))
        .update("\n")
        .update(body.trim())
        .digest("hex");
}
```

**Flow:** serialize → **re-parse and validate the bytes before touching disk** → write hidden pid+timestamp temp at 0600 → verify target still hashes to `expectedContentHash` → publish via rename (replace) or hard-link (`createOnly`: link(2) fails atomically if the target appeared since the pre-check) → always sweep the temp. Reads and writes refuse symbolic-link targets; every path resolves through `resolveSpecPath`, which requires a real `.task.md` strictly inside specsDir; `ensureSpecsDir` re-runs `assertSpecsDirSafe` before AND after mkdir, walking up to the nearest existing ancestor and comparing realpaths against the canonical workspace root.
**Invariant:** a stale writer can never silently replace newer human edits — it fails loudly ("changed/disappeared before update"); creation is atomic even under races; nothing outside the specs directory is ever written or followed through symlinks. The hash canonicalizes formatting (trimmed body), so whitespace-only churn does not false-positive.
**Probe:** no dedicated vitest suite for this class (coverage caveat) — behavior is pinned indirectly by `agenda-task-manager.test.ts` (:475-497 zero-artifact create failure; :887-921 raw invalid edit cannot corrupt terminal tasks) and exercised directly in the recovery fixture at :836-851. Byte-exact probes this pass: `linkSync(temporaryPath, target)` :154, `task spec changed before update` :211, symlink refusals :110/:131, escape guard :234.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "agenda task spec file store content hash", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.specs.task-spec-file-store.AgendaTaskSpecFileStore.assertExpectedContent" });
await mcp.codebase_memory.check_index_coverage({ project: "cline", paths: ["sdk/packages/core/src/tasks/specs/task-spec-file-store.ts"] });
```

## Verdict
Adopt validate-before-write, temp+rename publication, expected-content-hash CAS checked between staging and publish, link-based createOnly, and symlink/containment refusal. Adapt the file format, hash canonicalization, and directory layout to your host. Omit the `.task.md` suffix rule unless you also want watcher-greppable extensions. Runner caveat: no direct test runner for this class upstream here; evidence = indirect suite reads + byte-exact source probes + live retrieval.
