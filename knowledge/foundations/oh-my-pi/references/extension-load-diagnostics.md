<!-- capsule-v2 -->
# Extension load diagnostics and the not-initialized boundary — what should startup look like when third-party modules fail to load, and what can they safely call while loading?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** How do you surface per-extension load failures at startup without leaking paths or stack noise, and how do you make illegal during-load action calls impossible to miss?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/extensions/load-errors.ts:formatExtensionLoadNotifications` (:1-13 whole); `extensions/loader.ts:ExtensionRuntime` throwing stubs (:80-155) + `LoadExtensionsResult.errors` accumulation (:588-608); direct test `test/extensibility/extension-load-notifications.test.ts` (:1-26 whole).
**Signature:** `formatExtensionLoadNotifications(errors: Array<{ path: string; error: string }>): string[]`; `class ExtensionRuntime implements IExtensionRuntime` with every action method throwing.
**Data Shape:** one user-visible line per failed path: `Failed to load extension <short-path>: <one-line error>`.

### Decisive source
```ts
const displayPath = truncateToWidth(replaceTabs(shortenPath(path)), TRUNCATE_LENGTHS.CONTENT);
const displayError = truncateToWidth(replaceTabs(error.replace(/\s+/g, " ").trim()), TRUNCATE_LENGTHS.LONG);
messages.push(`Failed to load extension ${displayPath}: ${displayError}`);
// loader.ts: actions are throwing STUBS until init swaps them, so an extension calling
// sendMessage/appendEntry/setModel during its factory gets a typed error instead of a no-op:
sendMessage(): void { throw new ExtensionRuntimeNotInitializedError(); }
// ("Action methods cannot be called during extension loading.")
```
**Flow:** import/bind failures collected as `{path, error}` strings (never thrown past loadExtensions) -> startup formats each through shortenPath (home dir collapsed to ~), tab/newline collapse, width truncate -> TUI and print paths render identical single lines. Registration methods meanwhile write into per-extension collections; ONLY action methods (runtime-dependent) throw until initialize wires real implementations.
**Invariant:** (1) notification lines contain no raw home dir, no newline, no tab (pinned by test: `not.toContain(homeDir)` / `not.toContain("\n")` / tail truncated); (2) load errors never abort sibling extensions — errors array is parallel to extensions array; (3) the during-loading API surface is partitioned: registrations OK, actions throw typed ExtensionRuntimeNotInitializedError.
**Probe:** `test/extensibility/extension-load-notifications.test.ts` asserts startsWith "Failed to load extension ~/omp-notification-fixture/plugin", contains "name/extension.ts: SyntaxError: Missing named export at extension loader", and excludes home dir/newlines/tabs/tail-marker.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "formatExtensionLoadNotifications ExtensionRuntimeNotInitializedError", limit: 10 });
```

## Verdict
Adopt: sanitized single-line startup notifications + typed throwing-stub boundary for not-yet-wired actions. Adapt: your truncation widths and path-shortening helper. Omit: nothing else — both halves are directly portable.
