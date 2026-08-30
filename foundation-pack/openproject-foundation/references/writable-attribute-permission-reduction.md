<!-- capsule-v2 -->
# Writable-attribute permission reduction — how does a contract decide which attributes a given user may write at all?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** How do I port an authorization model where field-level writability = declared attributes − runtime conditions − per-user permissions, computed lazily per contract instance?

## Declarative attribute DSL reduced by conditions then permissions
**Path/Symbol:** `app/contracts/base_contract.rb:BaseContract` (DSL :84–115; reduction :214–270); WP override `app/contracts/work_packages/base_contract.rb:reduce_by_writable_permissions` (:664–671).
**Signature:** class macros `attribute(name, writable: nil|false|#call, permission: Symbol|Array, &validation_block)`, `attribute_alias(db_name, outside_name)`, `default_attribute_permission(perm)`; instance `writable?(attribute)` / memoized `writable_attributes`.
**Data Shape:** class-level registries: `writable_attributes` array, `writable_conditions` hash, `attribute_permissions` hash, `attribute_aliases` hash (`_id` suffix canonicalized via `delete_suffix("_id")`).

### Decisive source
```ruby
def reduce_by_writable_permissions(attributes)
  attribute_permissions = collect_ancestor_attributes(:attribute_permissions)
  attributes.reject do |attribute|
    canonical_attribute = attribute.delete_suffix("_id")
    permissions = attribute_permissions[canonical_attribute] ||
      attribute_permissions["#{canonical_attribute}_id"] ||
      attribute_permissions[:default_permission]
    next unless permissions
    next if permissions.any? do |perm|
      user.allowed_based_on_permission_context?(perm,
        project: project_for_permission_check,
        entity: entity_for_permission_check)
    end
    true
  end
end

# WorkPackages::BaseContract narrows further:
def reduce_by_writable_permissions(attributes)
  if already_in_readonly_status?
    super & %w(status status_id)   # readonly status ⇒ only status transitions
  else
    super
  end
end
```

**Flow:** collect ancestor writables (+aliases, + custom fields from `model.available_custom_fields`) → drop attributes whose `writable:` condition evaluates false per instance → drop attributes whose permission list the user holds NONE of (project/entity derived from the model: `model.project` vs Project itself). WP contracts additionally intersect with `%w(status status_id)` while in a readonly status.
**Invariant:** fail-closed: an attribute with permissions the user doesn't hold disappears from the writable set (mass-assign filters elsewhere rely on this); condition lambdas are evaluated per instance, not at boot. The `dup` in `collect_ancestor_attributes` (:193–212) is load-bearing — combining in place would mutate memoized CLASS state and leak superclass attributes into subclasses.
**Probe:** Deterministic source anchors above; no single dedicated unit spec for the reduction (exercised across contract specs). Recorded caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "writable attributes permission reduce conditions contract attribute alias", limit: 10, fields: ["signature"] });
// top hits: BaseContract.reduce_by_writable_conditions base_contract.rb:239-246; reduce_by_writable_permissions :248-270; WP override work_packages/base_contract.rb:664-671; Users/Projects overrides
```

## Verdict
Adopt the three-stage reduction (declared → conditioned → permitted) with `_id` canonicalization and any-of permission semantics. Adapt `allowed_based_on_permission_context?` to host authz; keep project/entity context derivation. Omit Disposable::Twin machinery if not porting form twins — the registries are plain class-level hashes. Coverage: no_recorded_issue ×2 paths.
