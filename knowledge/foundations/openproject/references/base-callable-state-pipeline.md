<!-- capsule-v2 -->
# BaseCallable state pipeline — how does a service object normalize arguments and thread shared side-channel state to its result?

**Source:** OpenProject GPL-3.0 `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory `openproject`. **Question:** Where do service params come from, and how can sibling services share non-result state (e.g. "created ids") across one logical operation?

## call → perform with around_call state assignment
**Path/Symbol:** `app/services/base_services/base_callable.rb:BaseServices::BaseCallable` (:31–85).
**Signature:** `.call(*args)` (class method from `self.call = new.call` convention upstream); `with_state(state = {}) -> self`; protected `perform(*args)`; private `assign_state`, `extract_options!(args)`.
**Data Shape:** trailing Hash (or strong-params object responding to `permitted?`/`to_h`) is popped and deep-symbolized into `params`; everything before it stays positional args for `perform`. State is a `Shared::ServiceState` struct-like builder.

### Decisive source
```ruby
around_call :assign_state

def call(*args)
  self.params = extract_options!(args).deep_symbolize_keys

  run_callbacks(:call) do
    perform(*args)
  end
end

def assign_state
  yield.tap do |service_result|
    service_result.state = state
  end
end
```

**Flow:** caller → `call(args…, options_hash)` → params normalized → ActiveModel `:call` callbacks wrap `perform` → returned ServiceResult gets the service's state attached (`yield.tap`). Callers may pre-seed with `.with_state(existing)` so a chain of services accumulates into ONE state object.
**Invariant:** `perform` must return a ServiceResult (state assignment taps it); subclass responsibility is enforced by raising `SubclassResponsibilityError`. Params are symbolized — downstream code must use symbol keys.
**Probe:** `spec/services/base/base_callable_spec.rb:56–73` — result is a ServiceResult, `result_state.test == "foo"`, and pre-seeded `with_state(bar:)` survives alongside values set during perform.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openproject", query: "BaseCallable with_state assign_state around_call perform", limit: 10, fields: ["signature"] });
// top hits: assign_state :69-73, with_state :47-50, perform :61-63, call :38-44 (base_callable.rb)
```

## Verdict
Adopt the callable-service envelope (trailing-options extraction, around-hook state injection, subclassResponsibility guard) as the base of any ported service kernel. Adapt `Shared::ServiceState` shape to host needs; keep it attachable to results rather than global. Omit Rails `ActiveModel::Callbacks` machinery if the host has no equivalent (a plain ensure/return works). Coverage: no_recorded_issue @ gen 2026-08-25T20:01:07Z; direct spec read, not executed in lane.
