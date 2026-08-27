<!-- capsule-v2 -->
# Write-tool proposal envelope — tools that never write, batch into one card, and report skips

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** What should an LLM "write" tool return so a human can approve N heterogeneous mutations without the agent ever touching the database?

## Three abstract bases, one envelope
**Path/Symbol:** `packages/Chat/src/Tools/BaseWriteCreateTool.php` (`handle` :87-191, `schema` :57-85); `BaseWriteUpdateTool.php` (`handle` :70-142, `schema` :53-68); `BaseWriteDeleteTool.php` (`handle` :49-105, `actionData` :133-149); shared context trait `Tools/Concerns/WithConversationContext.php` (whole, 22L).
**Signature:** `handle(Request $request): string` (JSON); abstract hooks: `modelClass()`, `actionClass()`, `entityType()`, `entityLabel()`, `entitySchema(JsonSchema)`, `extractRecordData()/extractActionData()`, `buildRecordDisplay()/buildDisplayData()`, `validateRequest()/validateRecord(): ?string`.
**Data Shape:** Result = `{type: 'pending_action', pending_action_id, action, entity_type, operation, data, skipped?, display, meta:{agent_should_stop:true}}`; stored `action_data` for batches = `{_batch: true, records: [{_record_id, _model_class, ...}]}`, single delete = `{_record_ids: [...]}`.

### Decisive source
```php
$model = $modelClass::query()
    ->whereBelongsTo($user->currentTeam)   // tenant scope BEFORE anything else
    ->whereKey($id)->first();
if ($user->cannot('update', $model)) {    // policy check on the scoped model
    return json_encode(['error' => "You do not have permission to update this {$this->entityLabel()}."]);
}
...
$pending = resolve(PendingActionService::class)->createProposal(...);
return json_encode([
    'type' => 'pending_action', ...,
    'data' => array_diff_key($pending->action_data, array_flip(['_record_id', '_model_class'])),
    'meta' => ['agent_should_stop' => true],
]);
```

**Flow:** tenant-scoped fetch → policy check → custom-field validation (bridge capsule) → entity-specific validation hook → build display rows (old model passed for update diffs) → ONE `createProposal()` → JSON envelope. Creates take a `records[]` array (cap `config('chat.max_batch_size')`=25, error naming the cap, zero proposals on breach); deletes take `ids[]`, filter to deletable models, and return the difference as `skipped` — cross-team or missing ids never fail the call while ≥1 id is valid. Multi-record deletes become `_batch` items so the approval dock can approve/reject each row independently; a vanished record at approval time fails only its item.
**Invariant:** A write tool NEVER persists business data — it only creates a PendingAction and returns an envelope whose underscore-prefixed routing keys (`_record_id`, `_model_class`, `_record_ids`, `_batch`) are stripped from the model-visible copy. Errors go back as JSON `error` strings the model can read and self-correct from, never thrown exceptions. The optional `plan {original_request, position, total}` rides in create schemas for multi-step requests and is prompt-sanitized before storage.
**Probe:** `tests/Feature/Chat/BulkDeleteToolTest.php` — one proposal per 3-id batch with `_batch.records[]._model_class === Task::class` (:26-47), single-id shape `_record_ids` (:49-61), foreign/missing ids land in `skipped` while the rest is proposed (:63-77), per-item `approveItem/rejectItem` independence (:92-108), vanished-record item isolation (:110-125). `BatchSizeLimitTest.php` pins the cap boundary at exactly-3-of-configured-3 accepted, 4 rejected with no PendingAction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "relaticle", function_name: "relaticle.packages.Chat.src.Services.PendingActionService.PendingActionService.createProposal", direction: "inbound", depth: 1 });
```

## Verdict
Adopt the envelope + one-proposal-per-batch contract for any agent that mutates durable state through human review. Adapt Laravel policy calls and the Filament-side dock to your stack; keep underscore-private action-data namespacing — it is what lets the executor carry routing metadata the model must not see. Omit the concrete CRM entity hooks.
