<!-- capsule-v2 -->
# Flagged org-cipher sync fan-out — how do I notify "the right users" about an org-scoped change when the delivery fabric can't address collections?

**Source:** Bitwarden server AGPL-3.0 `main@ac309aa19ed351406a56032d5f26a7a9a99f4abd`; Codebase Memory `server`. **Question:** When a cipher changes in an organization, who gets told, and what happens while the feature flag is off?

## Vault sync push service
**Path/Symbol:** `src/Core/Vault/Services/Implementations/CipherSyncPushService.cs:41–122` (`PushCipherAsync`); consumers `PushSyncCipherCreate/Update/DeleteAsync` :31–39 (delete reuses `PushType.SyncLoginDelete`).
**Signature:** `private async Task PushCipherAsync(Cipher cipher, PushType pushType, IEnumerable<Guid>? collectionIds)`.
**Data Shape:** payload `SyncCipherPushNotification { Id, UserId?, OrganizationId?, RevisionDate, CollectionIds? }`; flag `FeatureFlagKeys.OrgCipherPushFanout`; repos `GetCollectionIdsByCipherIdAsync` / `GetUserIdsByCollectionIdsAsync`.

### Decisive source
```csharp
if (!_featureService.IsEnabled(FeatureFlagKeys.OrgCipherPushFanout))
{
    // Device registrations in Notification Hub and Relay are not collection-aware,
    // so we cannot safely fan out to individual users on those mobile engines.
    // Restrict to the non-mobile (SignalR) path, which routes by organizationId.
    await _pushNotificationService.PushAsync(new PushNotification<SyncCipherPushNotification>
    {
        Type = pushType, Target = NotificationTarget.Organization,
        TargetId = cipher.OrganizationId.Value, /* … */ ExcludeCurrentContext = true,
        NonMobileOnly = true,
    });
    return;
}
var collectionIdList = collectionIds?.Distinct().ToList() ?? [];
if (collectionIdList.Count == 0)
{
    collectionIdList = [.. await _collectionCipherRepository.GetCollectionIdsByCipherIdAsync(cipher.Id)];
    if (collectionIdList.Count == 0)
    {
        _logger.LogWarning("Skipping push notification for organization cipher {CipherId} … no collection IDs were provided or found.");
        return;
    }
}
var userIds = await _collectionCipherRepository.GetUserIdsByCollectionIdsAsync(collectionIdList);
await Task.WhenAll(userIds.Select(userId => _pushNotificationService.PushAsync(
    new PushNotification<SyncCipherPushNotification> { Target = NotificationTarget.User, TargetId = userId, /* … */ })));
```

**Flow:** org cipher? → flag OFF ⇒ ONE coarse org-targeted notification marked `NonMobileOnly=true` (mobile engines skip it entirely; only SignalR-class engines deliver, resolving membership at receive time). Flag ON ⇒ dedupe caller-supplied collection ids; if empty, look them up from the DB; still empty ⇒ loud warning + silent return (no notification at all); else resolve user ids per collection and emit one user-targeted notification each via `Task.WhenAll`. Personal ciphers (no OrganizationId): user-targeted single send; neither user nor org ⇒ plain return.
**Invariant:** (1) the flag toggles between two *correctness* postures, not volumes — coarse-broadcast-under-addressing-constraint vs precise-per-user fan-out; (2) empty-collection resolution is fail-SILENT-with-warning by design (a cipher in no collection notifies nobody rather than everyone); (3) `ExcludeCurrentContext=true` on every path so the editing device never double-handles its own change; (4) revision date travels with every variant so clients can ignore stale deliveries.
**Probe:** `test/Core.Test/Vault/Services/CipherSyncPushServiceTests.cs` read FULL-RANGE (:16–280, pass 2): personal create/update/delete each pin Type/Target/TargetId/Payload (:18–72), and personal delete maps to `PushType.SyncLoginDelete` — a naming quirk to preserve or consciously rename; `…_PersonalCipher_NoUserId_NoPush` (:74–86) pins zero pushes when UserId is null; flag-off row :88–110 asserts `NonMobileOnly == true` + Organization target; flag-on rows :112–147/:207–242 assert one PushAsync per user with `Payload.UserId == TargetId`; delete-with-empty-ids :149–183 pins the repo fallback chain (`GetCollectionIdsByCipherIdAsync` → `GetUserIdsByCollectionIdsAsync`) and that returned collection ids travel in `Payload.CollectionIds`; `Array.Empty<Guid>()` fallback :244–279 documents it exists for SoftDelete/Restore callers; empty-after-fallback :185–205 pins warning + zero pushes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "server", query: "PushCipherAsync OrgCipherPushFanout GetUserIdsByCollectionIdsAsync", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: flag-as-degraded-delivery-mode pattern; dedupe→DB-fallback→loud-skip collection ladder; per-user fan-out only after membership resolution. Adapt: `NonMobileOnly` to your own engine-capability axis (here it is explicitly transient, `[EditorBrowsable(Never)]`, slated for removal with the flag). Omit: PushType enum semantics and client-side sync handling.
