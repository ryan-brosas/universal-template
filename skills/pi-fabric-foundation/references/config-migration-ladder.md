<!-- capsule-v2 -->
# Config migration ladder — how do you evolve a persisted config through named versions without ever losing user values?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for stepping an untrusted on-disk document up to the current config schema?

## Connected graph-selected seam
**Path/Symbol:** `src/config-migrations.ts` — `migrateFabricConfigDocument` (:104-134), `configVersion` (:90-102), `migrations` table (:32-88), `mergeObjects` (:20-30); `CURRENT_FABRIC_CONFIG_VERSION = 3` (:1).
**Signature:** `migrateFabricConfigDocument(input)` → `{ document, fromVersion, toVersion, appliedVersions, changed }`; input is NEVER mutated (`structuredClone` at :109).
**Data Shape:** `configVersion: number` stamped on every step; migration rows `{ from, to, migrate(doc) }` where `to === from + 1` is ENFORCED by the runner; legacy keys `subagents`, `ui.showNestedToolCalls`, `ui.nestedToolDebounceMs`.

### Decisive source
```ts
      const legacy = migrated.subagents;
      const canonical = migrated.agents;
      if (legacy !== undefined) {
        if (canonical !== undefined && isObject(legacy) !== isObject(canonical)) {
          throw new Error(
            "Fabric configuration cannot merge legacy subagents with a malformed agents section",
          );
        }
        migrated.agents = isObject(legacy) && isObject(canonical)
          ? mergeObjects(legacy, canonical)     // canonical wins per-key
          : canonical ?? legacy;
      }
      delete migrated.subagents;
```

**Flow:** validate the version stamp FIRST (missing ⇒ 0; non-integer/negative ⇒ throw; NEWER-than-supported ⇒ throw — never silently downgrade), then walk `version → CURRENT` one step at a time, stamping `configVersion` after each rung and recording it in `appliedVersions`. v0→1 folds `subagents` into `agents` (recursive deep merge, canonical section wins per key, TYPE-MISMATCH between the two = loud throw rather than discarding legacy values). v1→2 and v2→3 rename UI keys (`showNestedToolCalls→showAgentToolPreview`, `nestedToolDebounceMs→updateDebounceMs`) with explicit-wins semantics (existing canonical value is kept over the legacy one) and no-input-no-op behavior. Post-loop guard re-checks that no removed key survived.
**Invariant:** migrations are total and fail-loud — a missing rung throws ("No Fabric configuration migration exists for version N") instead of skipping; ambiguous merges throw instead of silently dropping either side's data; already-current documents pass through with `changed: false`; callers own persistence (atomic write + permission preservation live in the loader, pinned by its tests, not in this module).
**Probe:** `tests/config-migrations.test.ts:34` ("migrates the legacy agent section without mutating its input"), `:66` ("rejects an ambiguous malformed canonical section instead of discarding legacy values"), `:72` ("rejects invalid, future, and legacy keys in current documents"), `:208` ("keeps an explicit ui.showAgentToolPreview value over the legacy key").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "migrateFabricConfigDocument subagents agents configVersion migration", limit: 5, fields: ["signature", "name", "file"] });
```
