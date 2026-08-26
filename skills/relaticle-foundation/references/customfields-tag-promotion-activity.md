<!-- capsule-v2 -->
# Option promotion + activity attribution — idempotent tag growth and normalized-change logging

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do free-typed values grow a field's option list safely, and how does the activity log avoid recording changes the user never made?

## EnsureTagOptionsExist + CustomFieldValueObserver
**Path/Symbol:** `app/Actions/CustomFields/EnsureTagOptionsExist.php` (whole, 69L); `app/Observers/CustomFieldValueObserver.php` (whole, 159L): `saved()` (:22-39), `updated()` (:46-64), `normalize()` (:114-125), `describe()` (:94-112).
**Signature:** `EnsureTagOptionsExist::execute(CustomField $field, mixed $values): void`; observer bound via `#[ObservedBy]` on the App-level value model.
**Data Shape:** Activity payload: `custom_field_changes: [[code, label, type, old{value,label}, new{value,label}]]`, event `custom_field_changes`.

### Decisive source
```php
try {
    $field->options()->create([...]);
} catch (UniqueConstraintViolationException) {
    // A concurrent import/edit created this option first — the option
    // now exists, so treat it as a no-op rather than failing the row.
}
$existing[$key] = true;
```
Promotion gate lives on the model: `promotesValuesToOptions() = acceptsArbitraryValues && !withoutUserOptions` — tags-input promotes; email/phone/link accept arbitrary values but own no option list and are excluded. The observer's updated() guard: "A normalization-only rewrite (e.g. a link field stripping its URL scheme on save) is not a user edit — comparing the field-type-normalized old and new values keeps the timeline from attributing a change the user never made" (:56-61), plus `wasChanged($valueColumn)` before any work.

**Flow:** value save → observer.saved short-circuits on blank json_value (multi-value fields only) → promotion action trims/dedups candidates case-insensitively, appends after current max sort_order, races resolved by catch-and-continue → observer.updated logs ONLY when the type-normalized old ≠ new, describing choices as labels not raw IDs (arbitrary fields fall back to the stored string).
**Invariant:** Race tolerance is mandatory (unique violation = success); log attribution must compare through the SAME normalizer the field type applies on write, or every save looks like an edit.
**Probe:** `tests/Feature/ActivityLog/CustomFieldActivityTest.php` + executor tests :2403/:2428/:2443 (promotion, CI dedup, no-promotion-for-email).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "EnsureTagOptionsExist execute CustomFieldValueObserver updated normalize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt insert-race-as-success for option promotion and normalize-before-diff for change feeds. Adapt the activity-log library calls. Omit CRM-specific option caps. Direct tests cover both planes.
