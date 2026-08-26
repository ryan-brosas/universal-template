<!-- capsule-v2 -->
# ChangedBySystem attribution — how does a model distinguish user-caused changes from system/calculated ones?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** When defaults and derived values are written during the same mutation as user input, how do downstream validators/journals know which changes the USER actually made?

## change_by_system block + changed_by_user diff
**Path/Symbol:** `lib/open_project/changed_by_system.rb:OpenProject::ChangedBySystem` (:59–122).
**Signature:** `change_by_system { } -> block value`; `changed_by_system(attributes = nil) -> Hash`; `changed_by_user -> Array<String>`; private `non_no_op_changes`, `changes_compared_to(prior)`, `model_changes`.
**Data Shape:** `@changed_by_system` memoized hash of attribute ⇒ [old, new] pairs; `model_changes` = AR `changes` merged with `custom_field_changes` when the model is customizable.

### Decisive source
```ruby
def change_by_system
  prior_changes = non_no_op_changes
  ret = yield
  changed_by_system(changes_compared_to(prior_changes))
  ret
end

def changed_by_user
  (model_changes.reject { |key, change| changed_by_system[key] == change }).keys
end

def changes_compared_to(prior_changes)
  model_changes.select { |c| !prior_changes[c] || prior_changes[c].last != model_changes[c].last }
end
```

**Flow:** snapshot current changes → yield (service writes defaults/derived values inside the block, e.g. SetAttributesService's calculated plane) → record only NEW or newly-changed attributes as system-caused → consumers ask `changed_by_user`. Because VALUES are tracked, a default set before mass assignment and then overwritten by it correctly flips back to user-attributed.
**Invariant:** never wrap user-provided values in `change_by_system`; attribution must survive overwrites (compare last-value, not mere key presence). `non_no_op_changes` filters the `0→nil` AR artifact.
**Probe:** `spec/services/work_packages/set_attributes_service_spec.rb:447–453` — "sets the service's author" then "notes the author to be system changed" (author defaulting inside the service is attributed to the system).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "changed by system user attribution calculated default values tracking", limit: 10, fields: ["signature"] });
// top hits: ChangedBySystem.changed_by_user :97-99, change_by_system :84-92 (lib/open_project/changed_by_system.rb); ModelContract.changed_by_user app/contracts/model_contract.rb:136-141 consumes it
```

## Verdict
Adopt the snapshot-delta attribution wrapper for any model that mixes user input with computed writes in one pass. Adapt storage of the attribution hash (instance memo fine); keep value-comparison semantics. Omit custom-field merge if the host has no customizable layer. Coverage: no_recorded_issue @ gen 2026-08-25T20:01:07Z; spec anchor read directly.
