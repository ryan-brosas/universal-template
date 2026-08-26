<!-- capsule-v2 -->
# PendingAction human-approval protocol — how do AI-proposed writes get allowlisted, deduped, tenant-scoped, and resolved exactly once?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** what stands between an agent's proposed CRM mutation and the database?

## Allowlist gates + PENDING-only locked transitions + batch per-item resolution
**Path/Symbol:** `packages/Chat/src/Services/PendingActionService.php` (`ALLOWED_ACTION_CLASSES` :54-74, `createProposal` :80-133, `approve` :135-186, `approveItem/rejectItem` :215-286, `supersedePendingForConversation` :437-462, `resolvedForConversation` :474-500, `executeAction` :557-574, `resolveModel` :628-649).
**Signature:** `createProposal(User, ?string $conversationId, class-string $actionClass, PendingActionOperation $operation, string $entityType, array $actionData, array $displayData): PendingAction`; `approve(PendingAction, User): PendingAction`.
**Data Shape:** PendingAction row: action_class, operation (Create/Update/Delete), entity_type, action_data JSON (may embed `_model_class`/`_record_id`/`_record_ids`/`_batch.records`), display_data, status ∈ {Pending, Approved, Rejected, Expired, Superseded}, expires_at (+15min default), result_data.

### Decisive source
```php
// Idempotency across job retries. A continuation creates its proposal mid-stream; if a
// later chunk throws a transient error (429/529/503) the job is retried from the top and
// re-emits the identical tool call. ... Collapse an identical still-pending proposal ...
$pendingAction = PendingAction::query()->lockForUpdate()->findOrFail($pendingAction->getKey());
$this->validateResolvable($pendingAction);   // expired⇒mark+throw; resolved⇒throw
throw_if(($pendingAction->action_data['_batch'] ?? false) === true,
    RuntimeException::class,
    'Batch proposals resolve per item via approveItem()/rejectItem(), not approve().');
$result = $this->executeAction($pendingAction, $user);   // inside DB::transaction
$pendingAction->update(['status' => Approved, 'resolved_at' => now(), 'result_data' => $resultData]);
```
Tenant scoping around execution:
```php
$previousTenantId = TenantContextService::getCurrentTenantId();
TenantContextService::setTenantId($pendingAction->team_id);
try { /* execute */ } finally { TenantContextService::setTenantId($previousTenantId); }
```
Model resolution honors column/scope quirks:
```php
// CustomField uses tenant_id ... rather than the team_id column used by all other CRM
// models. ... CustomField has a global active scope that would exclude deactivated
// fields; skip it so an update-to-deactivate proposal can find the field regardless.
```

**Flow:** agent tool proposes → service checks identical-PENDING dedupe (byte-equal action_data in same conversation) → attach duplicate-create WARNING if same title was proposed/approved in last 15min → row persisted Pending w/ expiry. Human approves → transactional lock → resolvability checks → allowlisted action executed with CreationSource::CHAT → status Approved + result ids recorded. Batches: whole-batch approve REFUSED; each item resolves in its own transaction (partial progress survives), proposal finalizes Approved only if ≥1 created, else Rejected. New user message supersedes all still-pending actions (returns pre-update snapshot); every NEW turn re-injects terminal outcomes (newest 20, oldest-first) because replayed transcripts still claim pending.
**Invariant:** nothing executes unless (a) class is on a hardcoded allowlist, (b) row is PENDING and unexpired under lock, (c) tenant context equals the action's team for the duration of execution. Duplicate suppression distinguishes byte-identical retry (collapse) from same-title new proposal (warn, don't block).
**Probe:** `PendingActionAllowlistTest.php:12` (non-allowlisted refused), `BatchCreateApprovalTest.php` (:57 whole-batch refusal, :69 per-item approve, :118 item idempotency, :154 finalize rules, :236/:256 expired/resolved throw), `PendingActionSupersedeTest.php` (:36 supersede snapshot, :60 untouched resolved), `PendingActionTenantScopeTest.php:35` (tenant-scoped CF writes), `DuplicateProposalWarningTest.php` (:39 warn, :67 distinct titles silent, :83 byte-identical retry no warn), `BatchResolvedActionsTest.php` (:41/:92 result_ids shapes).
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "PendingActionService createProposal approveItem supersedePendingForConversation resolvedForConversation", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the full approval gate for any agent-write surface — static allowlist, locked PENDING-only state machine, expiry, per-item batch economics, supersede-on-new-turn, terminal-outcome re-injection into model context. Adapt action vocabulary and warning copy. Omit Filament/Livewire card rendering.
