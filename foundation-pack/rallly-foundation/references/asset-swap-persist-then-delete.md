<!-- capsule-v2 -->
# Asset swap persist-then-delete lifecycle — how do you replace a stored blob reference without orphaning the old object or deleting one that just became current?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What is the exact ordering of persist vs old-object delete, and which race is consciously accepted?

## replaceStoredAsset — DB first, after()-delete second, equality-guarded
**Path/Symbol:** `apps/web/src/lib/storage/asset-upload.ts:replaceStoredAsset` (lines 158–172, contract doc lines 146–157); instance-logo consumer `apps/web/src/features/instance-settings/mutations.ts:updateInstanceLogo` (lines 27–61); sibling consumers `features/user/actions.ts` (:135, :150) and `features/space/mutations.ts` (:107).
**Signature:** `replaceStoredAsset({ currentKey: string | null | undefined, nextKey: string | null, persist: () => Promise<void> }) → Promise<void>`.
**Data Shape:** keys are storage-object identifiers (or external URLs — `deleteStoredAsset` routes non-storage keys via `isStorageKey`); `nextKey: null` means "remove".

### Decisive source
```ts
/**
 * The replace-an-asset lifecycle: persist the new value, then delete the old
 * object after the response. Guards live here, once: a retry can resubmit
 * the key that is already stored (equality check), and the old value may be
 * externally hosted media (isStorageKey via deleteStoredAsset).
 *
 * Semantics are last-write-wins: currentKey is read before persist, so a
 * delayed duplicate of an older persist that lands after a newer one can
 * delete an object the concurrent write just made current. Closing that
 * window needs sign-time asset records (the planned Asset table), which is
 * where confirm-before-delete will live.
 */
export async function replaceStoredAsset({ currentKey, nextKey, persist }) {
  await persist();
  if (currentKey && currentKey !== nextKey) {
    after(() => deleteStoredAsset(currentKey));
  }
}
```
```ts
// updateInstanceLogo: read the CURRENT key, delegate the whole lifecycle
const instanceSettings = await prisma.instanceSettings.findUnique({
  where: { id: 1 }, select: { logo: true, logoDark: true, logoIcon: true },
});
await replaceStoredAsset({
  currentKey: instanceSettings?.[logoType],
  nextKey: imageKey,
  persist: async () => {
    await prisma.instanceSettings.update({ where: { id: 1 },
      data: { [logoType]: imageKey } });
    updateTag(instanceSettingsTag);   // cache invalidation INSIDE persist
  },
});
```

**Flow:** caller reads the currently-stored key → passes it as `currentKey` with a `persist` closure that writes the new key AND invalidates the feature's cache tag → lifecycle persists FIRST (DB is the source of truth; a leaked object is garbage, a dangling reference is a bug) → only if old ≠ new does the old object get deleted, deferred via `after()` so storage cleanup latency never delays the response. Retrying with an already-stored key is a no-op delete-wise because of the equality check.
**Invariant:** ordering is persist-before-cleanup, never the reverse — the failure asymmetry is deliberate: extra stored objects are invisible cost; missing referenced objects are broken images. The known race is WRITTEN DOWN in the function's own doc rather than hidden: `currentKey` is a pre-persist snapshot under last-write-wins semantics, so two interleaved replaces can let the older request's cleanup delete what the newer made current. Accepted until a sign-time Asset table enables confirm-before-delete. Three features share this ONE implementation ("guards live here, once") instead of three copies of the ordering decision.
**Probe:** no dedicated test for asset-upload.ts (caveat recorded). Byte anchors verified by direct read: `await persist();` :167, equality guard `currentKey && currentKey !== nextKey` :169, `after(() => deleteStoredAsset(currentKey))` :170; consumers confirmed by trace_path inbound on `updateInstanceLogo` (control-panel/branding/actions) plus grep for `replaceStoredAsset` (8 matches across user/space/mutations).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "replaceStoredAsset deleteStoredAsset updateInstanceLogo", limit: 10 });
```

## Verdict
Adopt the persist→equality-guarded→deferred-delete ordering verbatim for any keyed-blob replacement (avatars, logos, attachments); adapt `after()` to your framework's post-response hook; omit nothing silently — if you close the documented LWW window with an asset ledger, do it as the source plans it (confirm-before-delete against sign-time records), not by reverting to check-then-delete, which reintroduces the orphan leak it exists to avoid.
