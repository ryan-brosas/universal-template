<!-- capsule-v2 -->
# Contracted stage ladder — in what order does a mutating service validate, transform, and persist, and how are contract failures surfaced?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** How do I port a service pipeline where dry-style contracts gate persistence and every stage can veto downstream work?

## Success-gated perform ladder with convention-named contracts
**Path/Symbol:** `app/services/base_services/base_contracted.rb:BaseServices::BaseContracted#perform` (:59–72); validation mechanics in `app/services/concerns/contracted.rb:Contracted` (:48–78).
**Signature:** `initialize(user:, contract_class: nil, contract_options: {})`; hooks `validate_params`, `before_perform`, `validate_contract(call)`, `after_validate`, `persist`, `after_persist`, `after_perform` — each takes/returns a ServiceResult.
**Data Shape:** `user` is the acting principal injected at construction; `contract_options` is an opaque options hash forwarded into the contract; the model lives on `attr_accessor :model`.

### Decisive source
```ruby
def perform
  self.params, send_notifications = extract(params, :send_notifications)
  service_context(send_notifications:) do
    service_call = validate_params
    service_call = before_perform(service_call) if service_call.success?
    service_call = validate_contract(service_call) if service_call.success?
    service_call = after_validate(service_call) if service_call.success?
    service_call = persist(service_call) if service_call.success?
    service_call = after_persist(service_call) if service_call.success?
    service_call = after_perform(service_call) if service_call.success?

    service_call
  end
end

def validate_contract(call)
  success, errors = validate(model, user, options: contract_options)
  unless success
    call.success = false
    call.errors = errors
  end
  call
end
```

**Flow:** `send_notifications` is peeled out of params → context (transaction; see transactional-service-context capsule) → stages run strictly in order, each gated by `success?` so the FIRST failing stage's errors win → contract failure flips the shared result to failure and replaces its errors. Contract instantiation is `(model, user, options:)`; `contract_class=` raises ArgumentError for anything not descending `::BaseContract`.
**Invariant:** No stage after a failure runs — persistence never happens behind failed validation; `validate_and_yield` treats a falsy block return as failure (`[success, object&.errors]`). Convention: default contract class is `"#{deconstantize.pluralize}::CreateContract|UpdateContract".constantize`.
**Probe:** `spec/services/base_services/behaves_like_create_service.rb:98–118` — instance uses `<Namespace>::CreateContract`; when SetAttributes fails, subject is unsuccessful, exposes exactly those errors, and the model is not saved.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "validate_contract before_perform after_persist persist service stage", limit: 10, fields: ["signature"] });
// top hit: Projects::Concerns.NewProjectService.after_persist :41-48; BaseServices.Copy.after_persist :80-92; BaseContracted.after_persist :114-117 — hook overrides across namespaces
```

## Verdict
Adopt the ordered success-gated stage ladder + contract-class type check + convention-derived default contracts. Adapt naming conventions to host module layout; keep `validate(model, user, options:)` returning `[bool, errors]`. Omit the `alias_method :after_save, :after_perform` compatibility alias. Coverage: no_recorded_issue ×2 paths; shared-example spec read directly, suite not executed in lane.
