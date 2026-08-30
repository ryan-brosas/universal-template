<!-- capsule-v2 -->
# CLI launcher fast path — how do you make a hot subcommand start in milliseconds without forking your commander program or special-casing it deep inside?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you intercept one exact argv shape before the full CLI framework loads, and fall through cleanly for everything else?

## Exact-shape argv gate + dynamic fallback
**Path/Symbol:** `packages/cli/src/secret-get-fast-path.ts:trySecretGetFastPath` (4–19); name grammar `SECRET_NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/` (:2); bin entry `packages/cli/bin/localterm.mjs` (3-line launcher); real handler `commands/secret-get.ts:runSecretGet` (5–23); helper binary `native/localterm-secret-helper.c`, installed at `resources/localterm-secret-helper` (start.ts:53).
**Signature:** `const trySecretGetFastPath = async (arguments_: readonly string[], backend?: SecretBackend): Promise<boolean>`
**Data Shape:** matches ONLY `["secret", "get", <name>]` with a valid name; returns `true` if handled (process output/exit already set by `runSecretGet`), `false` ⇒ caller imports the full program.

### Decisive source
```js
// packages/cli/bin/localterm.mjs (the whole trick: 3 lines)
#!/usr/bin/env node
const { trySecretGetFastPath } = await import("../dist/secret-get-fast-path.js");

if (!(await trySecretGetFastPath(process.argv.slice(2)))) {
  await import("../dist/index.js");
}
```

**Flow:** bin imports ONLY the tiny fast-path module (no commander, no server SDK graph) → exact-shape test (arity 3, literal verbs, name regex) → on hit, dynamically import `commands/secret-get.js` and run it; on miss return false so the launcher lazily imports the full `index.js`. The secret value itself comes from the macOS Keychain via a compiled C helper (`localterm-secret-helper`) that resolves env-name→secret mappings concurrently with per-lookup timeouts, TERM-then-KILL reaping, and SIGINT propagation.
**Invariant:** any shape deviation — missing arg, extra arg (`valid extra`), `--help`, invalid name chars (`bad.name`) — falls through to the normal program untouched; the fast path preserves the command's EXACT stdout semantics (`value\n` via raw stdout write) and exit codes (missing secret ⇒ message + exitCode 1), so no caller can tell which path served it; backend is injectable for tests.
**Probe:** `packages/cli/tests/secret-get-fast-path.test.ts::"prints a synthetic value with the command's existing stdout semantics"` (:20), `::"falls through for non-exact shape"` table (:32 — all five shapes ⇒ false + get never called), `::"preserves the missing-secret exit and output behavior"` (:44). Helper contract: `tests/native-secret-helper.test.ts` (:79 hit/miss/oversize/NUL passthrough, :95 concurrent lookups <600ms for 8, :108 hung lookup ⇒ exit 71 + reaped; macOS-gated suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "trySecretGetFastPath runSecretGet SECRET_NAME_PATTERN", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.cli.src.secret-get-fast-path.trySecretGetFastPath", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the pattern — a tiny argv-shape gate imported by the bin, dynamic-importing the real handler on match and lazily importing the full program on miss, preserving byte-identical output/exit semantics; adapt the matched shape, the name grammar, and the secret backend to your host; omit the compiled Keychain helper (macOS-only product plumbing) unless you need native secret storage — inject a fake backend in tests instead. Direct tests cover the hit path, all five fall-through shapes, exit-code parity, and (macOS-gated) the helper's timeout/reap/concurrency contract.

