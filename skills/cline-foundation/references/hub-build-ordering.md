<!-- capsule-v2 -->
# Hub build ordering — a comparison whose antisymmetry, not transitivity, prevents mutual-retire loops

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** Given daemon records that may lack any build metadata (historical shapes), when may this build replace the running one versus attach to it?

## Tiered compare: equal id → epoch → release version → lexicographic; reuse gate
**Path/Symbol:** `sdk/packages/core/src/hub/discovery/index.ts:121-131` (`resolveHubBuildId`), `243-273` (`compareHubBuilds`), `286-292` (`resolveHubBuildIdentity`), `306-322` (`isManagedHubReusable`); watcher `hub/client/managed-hub-build-watcher.ts:75-124`.
**Signature:** `compareHubBuilds(a: HubBuildIdentity, b): number`; `isManagedHubReusable(record: HubProtocolMetadata & HubBuildIdentity, {self?}): boolean`; identity = `{buildId, buildEpochMs, coreVersion}`.
**Data Shape:** `buildId`: env `${HUB_BUILD_ID_ENV}` > embedded `__CLINE_CORE_RUNTIME_BUILD_ID__` > `source-<version>`. Epochs must be finite (`Number.NaN` and `0` corpus entries).

### Decisive source
```ts
const buildIdA = a.buildId?.trim(); const buildIdB = b.buildId?.trim();
if (buildIdA && buildIdB && buildIdA === buildIdB) return 0;        // same id wins over everything
const epochA = finiteEpochMs(a.buildEpochMs); const epochB = ...;
if (epochA !== undefined && epochB !== undefined && epochA !== epochB) return epochA < epochB ? -1 : 1;
const releaseA = parseReleaseComponents(a.coreVersion); ...
if (releaseA && releaseB) { const release = compareReleaseComponents(releaseA, releaseB); if (release !== 0) return release; }
if (buildIdA && buildIdB && buildIdA !== buildIdB) return buildIdA < buildIdB ? -1 : 1;   // stable tiebreak
return 0;                                                          // no comparable metadata = indistinguishable

// REUSE GATE: mismatch alone is not enough to replace...
export function isManagedHubReusable(record, options?) {
    const self = options?.self ?? resolveHubBuildIdentity();
    const compatibility = getManagedHubCompatibility(record, self.buildId ?? "");
    if (compatibility.compatible) return true;
    if (compatibility.reason !== "build_mismatch" && compatibility.reason !== "missing_build") return false;
    return compareHubBuilds(self, record) <= 0;   // reuse iff running daemon is same-or-newer than us
}
```

**Flow:** tiers — (1) identical trimmed buildId ⇒ equal regardless of epochs; (2) both epochs present+finite+different ⇒ order by time (beats version: "orders by build epoch before core version"); (3) both versions parse as releases ⇒ semver compare; (4) differing ids ⇒ lexicographic; else 0. Reuse gate: protocol-compatible ⇒ reuse; `unsupported_protocol` or other reasons ⇒ NOT reusable (replaceable); `build_mismatch`/`missing_build` ⇒ reusable only when the running hub is same-or-newer. Watcher turns persistent mismatches into a typed event with reason taxonomy: `unsupported_protocol` | `outdated_hub` (only when `compareHubBuilds(self, healthy) > 0`) | `build_mismatch` (newer hub or unorderable metadata ⇒ client-update prompt), skipping checks while the startup lock is held.
**Invariant:** **Antisymmetry**: two installs can never each decide to retire the other — `retires(a,b) && retires(b,a)` is false for every pair in the historical corpus. Reflexivity holds everywhere; transitivity holds ONLY for fully-populated identities (partial metadata makes "indistinguishable" non-transitive — documented and accepted). A record with no build metadata is attached-to, never retired.
**Probe:** `grep -cF 'return compareHubBuilds(self, record) <= 0;' sdk/packages/core/src/hub/discovery/index.ts` → 1; `grep -cF 'if (buildIdA && buildIdB && buildIdA === buildIdB) {' ...` → 1; test property: `grep -cF 'expect(retires(a, b) && retires(b, a)).toBe(false);' sdk/packages/core/src/hub/discovery/build-order.test.ts` → 1. Direct tests: `build-order.test.ts` ("never lets two builds retire each other", "attaches to a strictly newer Hub instead of downgrading it", "still replaces a protocol-incompatible Hub").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "compareHubBuilds isManagedHubReusable build identity epoch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tiered comparison + the ≤0 reuse gate + reason-taxonomy reporting; assert antisymmetry over YOUR historical metadata shapes when porting. Adapt the identity triple and env/embedded fallback chain. Omit npm dist-tag specifics. Runner-BLOCKED here; corpus properties pinned from source.
