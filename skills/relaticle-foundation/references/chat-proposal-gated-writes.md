<!-- capsule-v2 -->
# Proposal-gated writes — AI proposes, human approves, tenant context re-bound

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you let an AI assistant stage destructive CRM writes for human approval without cross-tenant leaks or double execution?

## PendingActionService approve/reject/batch
**Path/Symbol:** `packages/Chat/src/Services/PendingActionService.php` (whole, 752L): `createProposal()` (:80-133), `approve()` (:135-186), `approveItem()/rejectItem()` (:215-286), `validateResolvable()` (:544-555), `resolveModel()` (:628-649), `duplicateCreateWarning()` (:677-708).
**Signature:** `approve(PendingAction $pendingAction, User $user): PendingAction`; statuses Pending→Approved|Rejected|Expired|Superseded; expiry 15min default.
**Data Shape:** Row: team_id, user_id, conversation_id, message_id, action_class, operation, entity_type, action_data (JSON incl. `_model_class`, `_record_id`, `_batch`, `records[]`), display_data, result_data, status, expires_at. Allowlists as consts: 6 model classes, 18 action classes.

### Decisive source
```php
// The action executes the underlying CRM write... When approve() runs there may be no
// resolvable custom-fields tenant context... Without it the custom-fields TenantScope
// no-ops and saveCustomFields() iterates EVERY tenant's field definitions — writing
// value rows across all tenants (cross-tenant leak)...
$previousTenantId = TenantContextService::getCurrentTenantId();
TenantContextService::setTenantId($pendingAction->team_id);
try { $resolved = DB::transaction(function () use ($pendingAction, $user): PendingAction {
    $pendingAction = PendingAction::query()->lockForUpdate()->findOrFail($pendingAction->getKey());
    $this->validateResolvable($pendingAction);
    throw_if(($pendingAction->action_data['_batch'] ?? false) === true, RuntimeException::class,
        'Batch proposals resolve per item via approveItem()/rejectItem(), not approve().');
    ...
```
Idempotent proposal creation (:92-110): a retried job re-emitting the identical tool call collapses onto the still-PENDING duplicate instead of inserting another card. Batch items run per-item transactions "so partial progress survives a later item's failure — unlike approve(), which is atomic for the whole batch"; whole-batch approve is explicitly refused (:158-165).

**Flow:** chat tools never write directly — they create a PendingAction proposal card → approval path: tenant bracket + lockForUpdate + state validation + allowlist-checked action execution inside ONE transaction → batch Create/Delete proposals instead resolve item-by-item with idempotent `$items[(string)$index]` markers and finalize (Approved iff ≥1 approved, Rejected if all skipped) → same-title duplicate warning scans recent pending/approved proposals in the conversation.
**Invariant:** The tenant-context set/restore bracket must wrap EVERY write execution (its absence = cross-tenant value-row leak); resolution must be lock-then-validate-then-execute so a double-click cannot double-run; CustomField lookups need the vendor tenant column + activable-scope removal, not team_id.
**Probe:** `tests/Feature/Chat/BatchCreateApprovalTest.php` (:57 whole-batch refusal, :118 idempotent re-approve, :107 all-skipped⇒Rejected), `BatchCreateProposalTest.php`, `PendingActionSupersedeTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "PendingActionService approve createProposal supersedePendingForConversation validateResolvable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt propose→lock→validate→execute-in-tx with allowlists, per-item batch semantics, and the tenant bracket as the safety skeleton for any human-approved agent-write system. Adapt status vocabulary and expiry policy. Omit Filament card rendering. Strong direct-test coverage.
