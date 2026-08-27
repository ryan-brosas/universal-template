<!-- capsule-v2 -->
# Harness bootstrap marker idempotency — how do you seed a possibly-resued sandbox exactly once without locking?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A harness needs files+commands installed in a sandbox that may be fresh, snapshot-restored, or shared across sessions — what content-addressed marker makes application idempotent AND self-invalidating?

## Content-hash identity + marker-file fast path
**Path/Symbol:** `packages/harness/src/agent/internal/bootstrap-recipe.ts` — `hashHarnessBootstrap` (:20–59), `bootstrapMarkerPath` (:66–82), `applyBootstrapRecipe` (:94–166); `packages/harness/src/agent/internal/sandbox-bootstrap.ts` — `normalizeSandboxWorkDir` (:37–66), combined identity :206–242.
**Signature:** `hashHarnessBootstrap(recipe): Promise<string>` (16 hex chars); `applyBootstrapRecipe({session, recipe, identity, defaultWorkingDirectory})`.
**Data Shape:** recipe = `{ harnessId, bootstrapDir, files[{path,content}], commands[{command}] }`; marker = `${bootstrapDir}/.bootstrap-${identity}.ok`.

### Decisive source
```ts
const sortedFiles = [...recipe.files].sort((a, b) => a.path.localeCompare(b.path));
for (const file of sortedFiles) { pushString(file.path); pushString(file.content); }
pushString(JSON.stringify(recipe.commands));
pushString(String(BOOTSTRAP_SCHEMA_VERSION));   // shape bump invalidates ALL snapshots at once
...
const digest = await crypto.subtle.digest('SHA-256', buffer);
let hex = ''; for (let i = 0; i < 8; i++) hex += bytes[i].toString(16).padStart(2, '0');  // 16 chars
...
const existingMarker = await session.readTextFile({ path: markerPath });
if (existingMarker !== null) return;            // resumed/snapshot/shared sandbox ⇒ one cheap read
...
const mkdirResult = await session.run({
  command: 'mkdir -p "$BOOTSTRAP_DIR"',          // path travels as env var, NEVER interpolated into text
  env: { BOOTSTRAP_DIR: bootstrapDir },
});
```

**Flow:** identity hashes NUL-separated harnessId ‖ bootstrapDir ‖ sorted file path/content pairs ‖ JSON commands ‖ schema version; provider embeds it in the persistent sandbox NAME so any change (or a `BOOTSTRAP_SCHEMA_VERSION` bump) silently allocates a fresh snapshot; on first create the plan runs the recipe then writes the marker; every other entry (resumed sessions, provided sandboxes, post-create safety re-run in createSession) is a single marker read.
**Invariant:** Application is idempotent WITHOUT locks — the marker's existence IS the mutex; workDir must be relative, POSIX-separated, NUL-free, and may not escape (`..`) the sandbox default working directory; combined caller+harness identity = hash(schemaVersion ‖ recipeIdentity ‖ bootstrapHash ‖ workDir).
**Probe:** deterministic probes: `grep -c '.bootstrap-' packages/harness/src/agent/internal/bootstrap-recipe.ts` → `1`; `grep -c 'must not contain NUL' packages/harness/src/agent/internal/sandbox-bootstrap.ts` → `1`; direct tests `prepare-sandbox-for-harness.test.ts:108` ("returns the same identity for the same harnesses in a different order" — pins sort-stability), `harness-agent.test.ts:1857` ("built-in bootstrap uses recipe identity while snapshot identity includes workDir").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "hashHarnessBootstrap", limit: 3 });
// verified live @9d9a73f — total:1, rank#1 :20-59
```

## Verdict
Adopt content-hash identity + marker fast-path + env-var command passing for any idempotent environment seeding; adapt hash truncation length to host naming limits; omit the deprecation shim and keep the strict workDir ladder verbatim.