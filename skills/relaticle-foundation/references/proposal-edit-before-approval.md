<!-- capsule-v2 -->
# Proposal editing before approval — locked re-validation, per-code merge, display re-render, never executed

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How do you let a human fix a field on an agent's pending create-proposal — re-validating everything and re-rendering the card — without ever executing the action or drifting from the original validation contract?

## applyEdit: transaction, lock, split, validate, rebuild, re-render
**Path/Symbol:** `packages/Chat/src/Services/ProposalEditor.php` (`applyEdit` :43-87, `splitInput` :89-108, `validateCore` :110-125, `validateCustomFields` :137-163, `convertChoiceIdsToLabels` :170-207, `rebuildRecord` :251-298, `currentDisplayFields` :300-319, `persist` :321-349, `resolveRecord` :351-372, `assertEditable` :374-390); `packages/Chat/src/Support/ProposalCoreFields.php` (whole, 44L); driver `packages/Chat/src/Livewire/Chat/ProposalCard.php` (`saveField` :76-95, `flattenFormState` :111-128).
**Signature:** `applyEdit(PendingAction $pendingAction, User $user, array $input, ?int $index = null): PendingAction` — input keyed by field code; `$index` addresses one item of a `_batch` proposal; returns the refreshed row, still Pending.
**Data Shape:** `action_data` is the clean record (or `{_batch: true, records: [...]}`); `display_data` is `{title, summary, fields[]}` (or `items[{title,summary,fields[]}...]`); core keys per entity come from `ProposalCoreFields` (title/name + company's `account_owner_id`) — the single source of truth shared by server editor and docked card so the two sites cannot drift.

### Decisive source
```php
// Row lock inside a transaction; expiry is stamped lazily at edit time.
$locked = PendingAction::query()->lockForUpdate()->findOrFail($pendingAction->getKey());
$this->assertEditable($locked);   // create-only; pending+expired → mark Expired, then throw
...
// The locked ID↔label contract: incoming choice option IDs are converted BACK
// to labels first, because the validator re-translates labels → IDs and applies
// the configured rules. An ID that matches no option is left as-is so the
// downstream validator rejects it.
$converted = $this->convertChoiceIdsToLabels($editedCustomFields, $fields);
$result = $this->customFieldsValidator->validate($user, $entityType, $converted);
throw_if($result->error !== null, RuntimeException::class, (string) $result->error);
```
```php
// Only the edited codes change; every other custom field on the record is
// preserved. A code edited to an empty/invalid value (dropped by the
// validator, so absent from $cleanFields) is removed individually — never
// the whole map.
foreach (array_keys($editedCustomFields) as $code) {
    if (array_key_exists($code, $cleanFields)) {
        $merged[$code] = $cleanFields[$code];
        continue;
    }
    unset($merged[$code]);
}
if ($merged === []) { unset($record['custom_fields']); } else { $record['custom_fields'] = $merged; }
```

**Flow:** docked card's saveField flattens form state to `{code => value}` (custom fields lifted out of `custom_fields.<code>`) → `applyEdit` saves/restores the tenant context around a `DB::transaction` → `lockForUpdate` + create-only/expiry assertion → input split into core vs custom via `ProposalCoreFields::isCore` → core validated (non-empty title/name; company owner must be a team member via `TeamMembersContext::memberFieldError`) → choice ids converted back to labels and run through the SAME `CustomFieldsRequestValidator` the agent's write tools use → record rebuilt with per-code merge → `display_data` re-rendered by `ProposalDisplayBuilder` carrying forward existing rows (label-based dedup keeps custom rows from rendering twice, with or without a stored `type` key) → both blobs persisted (batch: index-addressed into `records[]`/`items[]`) → the action is NEVER executed and no continuation is dispatched; validation failures surface as a form error and leave the proposal Pending.
**Invariant:** Editing can only change what it was asked to change — untouched custom fields survive every edit, and an edit that clears a field removes exactly that field. The proposal's status machine is untouched by editing: it stays Pending, and expiry is enforced at edit time by stamping Expired before refusing. Core/custom classification lives in exactly one table so the UI and the server cannot disagree about which keys are first-class columns.
**Probe:** `tests/Feature/Chat/ProposalCardComponentTest.php` — edited custom field saved through ProposalEditor without executing (:498-515), other custom fields preserved when one is edited (:517-549), cancel leaves action_data untouched (:551-563), core title edit persists via applyEdit (:565-583), out-of-options choice rejected at form layer (:585-599), empty required name rejected, proposal stays pending (:601-620), batch item edit does not touch sibling records (:703-727). Display re-render dedup pinned in `tests/Feature/Chat/ProposalDisplayBuilderTest.php` (:73-124).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ProposalEditor applyEdit convertChoiceIdsToLabels ProposalCoreFields assertEditable lockForUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full re-validation-on-edit pattern for any human-editable pending mutation: lock the row, re-run the SAME validator the proposing agent used (converting values back into that validator's native vocabulary), merge per-field rather than replacing the payload, and re-render the display from the rebuilt record. Adopt a single shared core-vs-custom key table when two surfaces must classify fields identically. Adapt the batch index addressing and tenant-context save/restore to your multi-tenancy shape. Omit Filament form specifics. Coverage caveat: Codebase Memory MCP was not connected this pass; evidence is direct source+test reads at the pinned HEAD.
