<!-- capsule-v2 -->
# Driver delta two-tier contract — when does a backend implement native cursor delta versus adapt its listings into shared basicDelta?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** Where exactly is the line between "dumb" driver delta implementations and smart ones, and what must a native-cursor driver handle itself?

## Two tiers: basicDelta adapters vs native cursor drivers (+ quarantined broken tier)
**Path/Symbol:** adapter tier `packages/lib/file-api-driver-local.ts:71-83`, `file-api-driver-onedrive.ts:258-274`; native tier `file-api-driver-joplinServer.ts:98-142`; quarantine `file-api-driver-onedrive.ts:39-41` + `delta_BROKEN` :276-377; negotiation helper `packages/lib/file-api.ts:54-57` (`getSupportsDeltaWithItems`); entry `FileApi.delta` :441-444.
**Signature:** `driver.delta(path, options): Promise<PaginatedList>` where `PaginatedList = { items: ItemStat[]|{path,isDeleted:true}[], hasMore, context }`.
**Data Shape:** native cursor context `{ cursor?: string }`; adapter context is basicDelta's `{timestamp, filesAtTimestamp, ...}`; embedded-payload detection = `'jopItem' in items[0]`.

### Decisive source
```ts
// TIER 1 (adapter): OneDrive HAS a native API but currently drains listings into shared basicDelta:
const getDirStats = async (path) => {
    let items = [], context = null;
    while (true) {
        const result = await this.list(path, { includeDirs: false, context });
        items = items.concat(result.items); context = result.context;
        if (!result.hasMore) break;
    }
    return items;
};
return await basicDelta(path, getDirStats, options);

// TIER 2 (native): JoplinServer pages its own cursor endpoint:
const response = await this.api().exec('GET', `${this.apiFilePath_(path)}/delta`, query);
const stats = response.items.filter(item => {
    if (item.item_name.indexOf('locks/') === 0) return false;   // LockHandler owns these
    if (item.item_name.indexOf('temp/') === 0) return false;    // scratch space, not data
    if (item.item_name.indexOf('.resource/') === 0) return false; // driven by .md twin
    return true;
}).map(...);
...
} catch (error) {
    if (cursor && error.code === 'resyncRequired') { cursor = null; continue; } // full restart
    throw error;
}
// Server side pins the contract: ChangeModel.test.ts:148 expects invalid cursor → 'resyncRequired'
export enum ... { ResyncRequired = 'resyncRequired', }   // packages/server/src/utils/errors.ts:2

// Detection used by Synchronizer's fast path:
export const getSupportsDeltaWithItems = (deltaResponse: PaginatedList) => {
    if (!deltaResponse.items.length) return false;
    return 'jopItem' in deltaResponse.items[0];
};
```

**Flow:** `FileApi.delta` wraps any tier in tryAndRepeat → tier-1 drivers synthesize a full-listing function (possibly draining paginated `list()` internally) and hand it to the shared listing-diff algorithm owned by the basicdelta-failsafe capsule → tier-2 drivers return server-computed pages directly and own cursor lifecycle themselves, including the restart-on-invalid-cursor rule; the synchronizer sniffs each page via `getSupportsDeltaWithItems` to decide whether content rides inside the delta response or must be fetched separately. OneDrive demonstrates all three postures at once: working adapter (:258-274), quarantined `delta_BROKEN` native implementation kept for reference with its `BrokenDeltaOptions {context?:{nextLink}}`, and no regression risk to users.
**Invariants:** (1) a native-cursor driver MUST filter non-data prefixes (locks/, temp/, .resource/) client-side — the server streams everything under the root; (2) an invalid/expired cursor degrades to a FULL re-sync (clear cursor, retry) never to an error surfaced to the user; (3) empty first page ⇒ capability unknown ⇒ treat as no embedded payloads (getSupportsDeltaWithItems returns false on empty items) — absence of evidence defeats the fast path, safely; (4) both tiers honor the same PaginatedList shape, so the synchronizer stays tier-blind; (5) broken native implementations get quarantined under `_BROKEN` names instead of deleted — the reference code survives for the next attempt.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "return await basicDelta(path, getDirStats, options);" packages/lib/file-api-driver-onedrive.ts && grep -cF "error.code === '"'"'resyncRequired'"'"'" packages/lib/file-api-driver-joplinServer.ts && grep -cF "ResyncRequired = '"'"'resyncRequired'"'"'," packages/server/src/utils/errors.ts && grep -cF "'"'"'jopItem'"'"' in deltaResponse.items[0];" packages/lib/file-api.ts'` (anchored at repo root; expects 1 / 1 / 1 / 1). Direct tests: `packages/server/src/models/ChangeModel/ChangeModel.test.ts:148` (invalid cursor throws resyncRequired); `packages/lib/file-api.test.ts:150-154` parametrizes getSupportsDeltaWithItems.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "basicDelta FileApiDriverJoplinServer delta resyncRequired getSupportsDeltaWithItems BrokenDeltaOptions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: two-tier split with a common PaginatedList contract, prefix filtering + cursor-reset-restart duties for native tiers, sniffed embedded-payload capability, _BROKEN quarantine pattern. Adapt: which tier your backend can afford (native cursors need server support). Omit: basicDelta internals (owned by basicdelta-failsafe) and the synchronizer-side pagination loop (owned by delta-context-pagination).
