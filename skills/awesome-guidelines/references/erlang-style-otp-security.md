<!-- capsule-v2 -->
# OTP and security — are exports, process APIs, and input handling safe?

**Source:** Inaka §Misc/Tools; OTP Secure Coding STL-001/DSG-002/DSG-003/DSG-011. **Question:** Will misuse or untrusted input crash visibly instead of corrupting state?

## Export seam
**Path/Symbol:** `-module` attributes and OTP behaviour modules.
**Signature:** explicit `-export`; encapsulated `gen_server` API.
**Data Shape:** `{ok, Result} | {error, Reason}` on fallible public functions.

### Decisive pattern
```erlang
-module(worker).

-export([start_link/0, submit_job/1]).

-spec submit_job(map()) -> {ok, job_id()} | {error, validation_failed}.
submit_job(Payload) when is_map(Payload) ->
    gen_server:call(?MODULE, {submit, Payload}, 5000).

handle_call({submit, Payload}, _From, State) ->
    case validate(Payload) of
        {ok, Job} ->
            {reply, {ok, enqueue(Job, State)}, State};
        {error, Reason} ->
            {reply, {error, Reason}, State}
    end.
```

**Flow:** never `-compile(export_all)` or `-import` → wrap every cross-module `gen_server:call/cast` in same-module API function → return `{ok, _}` / `{error, _}` and let caller decide exceptions (DSG-002) → match restrictively — no catch-all when alternatives are known; match `[]` for empty lists → check `ok =` results instead of `_ =` (STL-001) → log handled errors with stack trace at appropriate level.
**Invariant:** raw `gen_server:call(other_mod, …)` from outside `other_mod`, silent `_ =` on fallible call, or catch-all `_` clause fails review.
**Probe:** grep `export_all`, `-import`, external `gen_server:call`; Dialyzer on API specs.

## Input seam
```erlang
status_from_binary(<<"active">>) -> active;
status_from_binary(<<"inactive">>) -> inactive;
status_from_binary(_) -> {error, invalid_status}.

safe_decode(Bin) ->
    try binary_to_term(Bin, [safe]) of
        Term -> {ok, Term}
    catch
        error:badarg -> {error, invalid_term}
    end.
```

**Flow:** map known external strings to atoms explicitly — avoid `binary_to_atom/1` on untrusted input (DSG-003) → deserialize only trusted data; `binary_to_term/2` with `[safe]`; never `file:consult/1` on untrusted paths (DSG-011) → avoid dynamic `apply(M, F, …)` when xref must track calls → no debug `io:format` in production `src/`.
**Invariant:** `binary_to_atom(Input)`, `binary_to_term(Bin)`, or debug IO in hot path fails security review.
**Probe:** grep `binary_to_atom`, `list_to_atom`, `binary_to_term(` without `safe`; Elvis/security rule pass.

## Verdict
Encapsulated OTP API, restrictive matches, safe atoms/deserialize, explicit exports. Learning note: `erlang-style-learning-note.md`.
