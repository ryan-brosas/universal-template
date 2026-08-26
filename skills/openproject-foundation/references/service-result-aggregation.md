<!-- capsule-v2 -->
# ServiceResult aggregation tree — how do composed services report one combined outcome without exceptions?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** When a service calls other services, what is the contract for combining their outcomes into a single success/failure answer that controllers and callers can consume?

## Result object with AND-semantics dependent tree
**Path/Symbol:** `app/services/service_result.rb:ServiceResult` (:42–388).
**Signature:** `ServiceResult.success(**opts) / .failure(**opts)`; `initialize(success: FAILURE, errors:, message:, message_type:, state:, dependent_results: [], result:)`; `merge!(other, without_success: false)`, `add_dependent!(dependent)`.
**Data Shape:** `success` boolean; `result` arbitrary object (usually an unsaved AR model); `errors` ActiveModel::Errors bound to the result model when it responds to `errors` (`new_errors_with_result` :370–375); `dependent_results` array of child ServiceResults.

### Decisive source
```ruby
def add_dependent!(dependent)
  merge_success!(dependent)

  inner_results = dependent.dependent_results
  dependent.dependent_results = []

  dependent_results << dependent
  self.dependent_results += inner_results
end

private

def merge_success!(other)
  self.success &&= other.success
end
```

**Flow:** factory (`success`/`failure`) → stages attach errors/dependents via `merge!`/`add_dependent!` → consumers branch with `on_success`/`on_failure`, chain with `bind` (short-circuits failure, returns `self`), transform with `map` (returns a dup carrying new result), project to flash via `apply_flash_message!` (`message_type` defaults `:notice`/`:error`). Pattern matching supported through `deconstruct_keys(:success, :failure, :result, :errors)`.
**Invariant:** A parent result is successful only if EVERY merged/dependent result is successful; failure must never raise — error text flows through `message` (joins `errors.full_messages`). The default initializer value for `success` is FAILURE: never construct bare `.new(success: truthy-thing)`.
**Probe:** `spec/services/service_result_spec.rb` (:61–64 "is false by default"; :90–94 factories accept the full initializer keyword set and return identical accessors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "ServiceResult dependent results merge success failure factories", limit: 10, fields: ["signature"] });
// top hit: openproject.app.services.service_result.ServiceResult.merge_dependent! (service_result.rb:385-387); also merge_success!, add_dependent! :218-226
```

## Verdict
Adopt the result-object-with-dependent-tree pattern (AND-success merge, model-bound errors, bind/map short-circuit) for any ported service layer. Adapt `human_attribute_name` delegation and flash-message coupling to the host's i18n/controller stack. Omit Redmine-lineage specifics (`ApplicationRecord.human_attribute_name` fallback). Coverage caveat: no_recorded_issue ×1 path @ gen 2026-08-25T20:01:07Z; spec read directly but suite not executed in lane (no DB/bundle).
