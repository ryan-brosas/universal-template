<!-- capsule-v2 -->
# Folder-watch watcher reconcile — when must an fs.watch be torn down and re-armed?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** Which automation edits require rebuilding the native watcher, and which can keep the existing one?

## recursive+cwd+filter signature governs rebuild
**Path/Symbol:** `packages/server/src/folder-watch-manager.ts:signatureOf` (:60–63) + `sync` (:84–102) + `startEntry` (:110–132).
**Signature:** `sync(automations: Automation[]): void`; `watch?: WatchFn` injectable so tests fire synthetic events deterministically.
**Data Shape:** `entries: Map<id, { watchers: WatchHandle[], signature, debounceTimer, postRunGraceTimer, postRunGraceActive }>`; signature = `` `${trigger.recursive}:${automation.cwd}:${automation.trigger.filter ?? ""}` `` for watch automations (`automation.cwd` otherwise).

### Decisive source
```ts
const watcher = this.watch(automation.cwd, { recursive }, (event, filename) => {
        this.onFsEvent(automation.id, event, filename);
      });
      // Don't keep the daemon alive on the watch alone (the http server does).
      watcher.unref?.();
      entry.watchers.push(watcher);
    } catch {
      // cwd doesn't exist or isn't watchable right now — leave the entry empty;
      // a later sync (after the directory is fixed) retries.
    }
```

**Flow:** sync filters the desired set (enabled ∧ active ∧ kind "watch") → stops entries whose signature changed → starts missing ones. startEntry arms ONE fs.watch per automation on its cwd; a failed arm (cwd missing) stores the EMPTY entry so a later sync retries — no crash, no permanent dead state. Every watcher is `.unref()`-ed; the HTTP server holds daemon liveness, not watches.
**Invariant:** The filter is part of the watch SIGNATURE but NOT of the armed watch — one watch serves any filter because filtering happens per-event in `onFsEvent`. Changing only the filter still rebuilds (cheap), but a porter who instead arms filter-specific watches multiplies watchers. Failed arms retry via later syncs; they never throw.
**Probe:** `packages/server/tests/folder-watch-manager.test.ts` (`rebuilds the watcher when the recursive flag changes` :141, `rebuilds the watcher when the filter changes` :222, `never arms a watcher for a schedule trigger` :154 — armed.size stays 0).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "FolderWatchManager sync startEntry fs.watch", limit: 10 });
```

## Verdict
Adopt the signature-reconcile + injectable-watch-factory + empty-entry-retry pattern; adapt to your fs abstraction. Directly tested with a fake watch factory under fake timers (fully deterministic).
