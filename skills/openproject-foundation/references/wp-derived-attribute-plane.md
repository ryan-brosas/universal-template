<!-- capsule-v2 -->
# WP derived-attribute plane — how does attribute-setting compute dates/progress and survive failed project moves?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** In what order are static, custom, and calculated work-package attributes applied, and what algebra derives the unspecified member of {duration, due_date, start_date}?

## Param-plane split + date-derivation algebra inside change_by_system
**Path/Symbol:** `app/services/work_packages/set_attributes_service.rb:WorkPackages::SetAttributesService` (`set_attributes` :43–56; derivation :102–189; project-move cleanup :274–294).
**Signature:** `set_attributes(attributes)` (private); `derivable_date_attribute`, `update_derivable_date_attribute`; `clear_semantic_identifier`.
**Data Shape:** params hash split into: attachment keys, version-replacement ids (`target_version_ids`/`observed_in_version_ids` → `*_replacements`), static assignable attrs (respond-to `key=` and not a custom field), calculated plane, custom-field attrs.

### Decisive source
```ruby
def set_attributes(attributes)
  validate_custom_fields = attributes.delete(:validate_custom_fields)
  set_attachments_attributes(attributes)
  set_versions_attributes(attributes)
  set_static_attributes(attributes)

  model.change_by_system do          # everything below is SYSTEM-attributed
    set_calculated_attributes(attributes)
  end

  set_custom_attributes(attributes)  # user-attributed custom fields
  set_custom_values_to_validate(attributes, validate_custom_fields)
end

# derivation order duration -> due_date -> start_date; presence rule before absence rule
def derivable_by_others_presence?(field)
  others = %i[start_date due_date duration].without(field)
  attribute_not_set_in_params?(field) && all_present?(*others)
end

def clear_semantic_identifier
  work_package.sequence_number = nil
  work_package.identifier = nil
end
```

**Flow:** planes in order → calculated plane wrapped in `change_by_system`: defaults for new records (priority/author/status/dates from parent or Setting), milestone unification (start=due, duration=1), derivable-date computation (milestone ⇒ duration=1 else working-day count), soonest-working-day shifting, progress derivation (status-based vs work-based mode class swap), type-change status reassignment, readonly-cause marking → custom fields last (user-owned). On project move: clear semantic identifier IN THE SAME UPDATE as `project_id=` (unique index `(project_id, sequence_number)`); on failure restore identifier for error messages.
**Invariant:** only the field NOT present in params is ever derived; both-others-nil ⇒ nothing derived; invalid duration (non-Integer or ≤0) aborts due/start derivation and is left to contract errors. Version-replacement clearing marks system override when the user passed none.
**Probe:** `spec/services/work_packages/set_attributes_service_spec.rb:553+` full date-algebra matrix ("sets the start date value"/"updates the duration"/…); :524–550 failed move with semantic identifiers — unsuccessful, identifier `"SRC-1"` restored on the instance, move not persisted.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "derivable date duration start due milestone schedule working days work package attributes", limit: 10, fields: ["signature"] });
// top hits: SetAttributesService.derivable_date_attribute :102-104, update_derivable_date_attribute :163-181, derivable_*_by_others_presence/absence :114-117/:134-136; WorkingDays.due_date working_days.rb:79-89
```

## Verdict
Adopt the param-plane ordering (attachments → versions → static → calculated(system) → custom(user)) and the two-rule derivation algebra with its fixed field order. Adapt working-day calendar + milestone semantics to host domain. Omit Redmine Setting globals (replace with config injection). Coverage: no_recorded_issue @ gen 2026-08-25T20:01:07Z; spec ranges read directly.
