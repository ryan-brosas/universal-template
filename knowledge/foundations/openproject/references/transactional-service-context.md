<!-- capsule-v2 -->
# Transactional service context — how does a failed service result roll the whole mutation back, and when is it serialized by a lock?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** How do I guarantee atomicity and per-resource serialization for a service run driven by returned results (not exceptions), while running as the acting user with notification control?

## Rollback-on-failure-result transaction, advisory-locked per model
**Path/Symbol:** `app/services/shared/service_context.rb:Shared::ServiceContext` (:35–71); lock wrapper `lib/open_project/mutex.rb:OpenProject::Mutex.with_advisory_lock_transaction` (:57–65).
**Signature:** `in_context(model, send_notifications:)`; `in_mutex_context(model, …)`, `in_user_context(…)`, `without_context_transaction(send_notifications:)`.
**Data Shape:** `model` nil ⇒ plain user context; non-nil (Update/Delete paths carry the persisted record) ⇒ advisory-lock context. `send_notifications` tri-state forwarded to journal notification config.

### Decisive source
```ruby
def in_mutex_context(model, send_notifications: nil, &)
  result = nil
  OpenProject::Mutex.with_advisory_lock_transaction(model) do
    result = without_context_transaction(send_notifications:, &)
    raise ActiveRecord::Rollback if result.failure?
  end
  result
end

# lib/open_project/mutex.rb:57-65
def with_advisory_lock_transaction(entry, suffix = nil, options = {}, &)
  lock_name = "mutex_on_#{entry.class.name}_#{entry.id}"
  lock_name << "_#{suffix}" if suffix
  options[:transaction] ||= true
  ActiveRecord::Base.transaction do
    with_advisory_lock(entry.class, lock_name, options, &)
  end
end

def without_context_transaction(send_notifications:, &)
  User.execute_as user do
    Journal::NotificationConfiguration.with(send_notifications, &)
  end
end
```

**Flow:** service perform → transaction begins → (optionally acquire pg advisory lock named `mutex_on_<Class>_<id>`) → run stages as the injected user with notification scope set → if the RESULT is a failure, raise `ActiveRecord::Rollback` (caught by the transaction; not an error) → return the result object either way.
**Invariant:** Failure is communicated by VALUE, but durability is still all-or-nothing — every partial write inside the ladder is rolled back. Lock name is class+id keyed; the file header documents why lock+transaction must wrap together (READ COMMITTED lost-update/journal-split rationale).
**Probe:** No dedicated unit spec for ServiceContext itself (covered transitively by integration specs such as `spec/services/work_packages/create_service_integration_spec.rb`). Recorded caveat: probe here is the source pair above; behavioral proof deferred to a provisioned-DB lane.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "advisory lock transaction rollback send_notifications user execute as service context", limit: 10, fields: ["signature"] });
// top hit: OpenProject.Mutex.with_advisory_lock_transaction lib/open_project/mutex.rb:57-65; ServiceContext.without_context_transaction :67-71; User.execute_as app/models/user.rb:592-598
```

## Verdict
Adopt rollback-by-result-value + advisory-lock-per-record + execute-as-user composition. Adapt the lock primitive to host DB (named advisory locks are Postgres-flavored); keep rollback semantics distinct from raised errors. Omit journal-notification coupling unless porting journals too. Coverage: no_recorded_issue ×2 paths @ gen 2026-08-25T20:01:07Z.
