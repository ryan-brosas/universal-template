<!-- capsule-v2 -->
# Hibernation persistence (atomic versioned snapshot) — how do you persist live terminal scrollback across a daemon restart without ever storing raw PTY control bytes?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What is the minimal safe on-disk format + write protocol for "restore my tabs and their rendered scrollback after restart"?

## Strict-schema envelope with fail-open reads
**Path/Symbol:** `packages/server/src/hibernate-store.ts:HibernateStore` (43–70); data model `HibernateTab` (6–11), `HibernateEntry` (13–17); zod schemas `hibernateTabSchema`/`hibernateEntrySchema`/`hibernateFileSchema` (19–39); constants `HIBERNATE_FILENAME="hibernate.json"`, `HIBERNATE_FILE_VERSION=1`, `HIBERNATE_SCROLLBACK_LINES=2_000`, `HIBERNATE_SCROLLBACK_MAX_CODE_UNITS=256*1024` (constants.ts:71–74).
**Signature:** `class HibernateStore { constructor(private readonly filePath: string); read(): HibernateEntry[]; write(entries: readonly HibernateEntry[]): void; }`
**Data Shape:** file = `{ version: 1, entries: [{ owner: string|null, windowId: string, tabs: [{ sessionId, cwd, shell, scrollback }] }] }`, all objects `.strict()`; `scrollback` is RENDERED TEXT WITH SGR STYLING ONLY (produced by `CaptureRenderer.captureNormal`, see capture-renderer.md) — raw PTY control bytes are never stored.

### Decisive source
```ts
// packages/server/src/hibernate-store.ts:41-42 (the whole security model)
// One compact file written during graceful daemon shutdown. Scrollback is
// rendered text with generated SGR styling; raw PTY control bytes are never stored.
...
// :46-54 — any read failure degrades to "nothing to restore", never throws
read(): HibernateEntry[] {
  try {
    const parsed = hibernateFileSchema.safeParse(
      JSON.parse(fs.readFileSync(this.filePath, "utf8")),
    );
    return parsed.success ? parsed.data.entries : [];
  } catch {
    return [];
  }
}
```

**Flow:** graceful shutdown → `SessionManager.hibernateEntries()` (session-manager.ts:371–399): for each managed session that has attached clients and is not an automation run → `await renderer.flush()` → build one tab `{sessionId: managed.id, cwd: lastEmittedCwd || cwd, shell, scrollback: renderer.captureNormal(2000, 256K)}` → group tabs under one entry per `owner\0windowId` key → `HibernateStore.write(entries)`. Next start reads the file, reopens each tab's shell in its old cwd, and replays the stored scrollback into a fresh renderer so the restored pane looks identical.
**Invariant:** `read()` NEVER throws — missing file, corrupt JSON, wrong-version payload (`version: 999`), and schema violations ALL return `[]`; writes are atomic via temp-file + rename with mode 0o600; the version literal pins forward-compat (old daemons refuse newer files by returning empty).
**Probe:** `packages/server/tests/hibernate-store.test.ts::"round-trips rendered tab snapshots"` (:20 — exact JSON shape incl. version), `::"returns an empty snapshot for missing, corrupt, or invalid files"` (:45 — not-json ⇒ [], version-999 ⇒ []).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "HibernateStore read write hibernateEntrySchema", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.session-manager.SessionManager.hibernateEntries", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the fail-open strict-schema envelope (`read` ⇒ `[]` on ANY anomaly), atomic 0o600 temp-rename writes, and the rendered-SGR-only scrollback payload (control bytes never persisted); adapt the file location, version constant, and the owner\0windowId grouping key to your host; omit the CDP-based workspace reconciliation on startup unless you are porting the whole daemon restart flow. Direct tests cover round-trip shape and all corrupt/missing/version-mismatch reads; caveat: end-to-end restore is exercised by `tests/hibernate-restart.test.ts`, not by this unit test.
