<!-- capsule-v2 -->
# Naming and types — are symbols OTP-idiomatic and Dialyzer-friendly?

**Source:** Inaka §Naming/Records/Misc; OTP STL-002 boolean blindness. **Question:** Can grep and Dialyzer distinguish variables, atoms, and public types?

## Naming seam
**Path/Symbol:** modules, functions, variables, records, messages.
**Signature:** snake_case modules/functions/atoms; CamelCase variables; `#mod_state`.
**Data Shape:** `-spec` and exported `-type` on public API.

### Decisive pattern
```erlang
-module(payment_gateway).

-type payment_status() :: authorized | declined | pending.

-record(payment_gateway_state, {
    conn :: pid(),
    timeout_ms :: pos_integer()
}).

-spec authorize(PaymentId :: binary(), Amount :: integer()) ->
          {ok, payment_status()} | {error, term()}.
authorize(PaymentId, Amount) ->
    gen_server:call(?MODULE, {authorize, PaymentId, Amount}).

handle_call({authorize, PaymentId, Amount}, _From, State) ->
    {reply, do_authorize(PaymentId, Amount, State), State}.
```

**Flow:** one module naming convention project-wide → functions/atoms/records lowercase with `_` → variables `CamelCase` without `_` → OTP state as `#payment_gateway_state{}` with `-type state()` → avoid boolean parameters — use atoms like `authorized | declined` → messages as atom or `{set_worker_pid, Pid}` tagged tuple → `-spec` every exported function; export custom types used in specs; use opaque types instead of sharing records.
**Invariant:** `badFunction`, `Variablename`, boolean arg controlling clause selection, or record in `-spec` fails review.
**Probe:** Elvis naming rules; Dialyzer on exported API; grep for `true | false` parameter patterns.

## Consistency seam
**Flow:** reuse same variable name for same concept across modules (`OrgId` everywhere) → macro names `ALL_UPPER_CASE` only for literal constants → avoid macros for module/function names.
**Invariant:** duplicated concept names or `?MODULE`-style indirection macros fail review.
**Probe:** cross-module concept grep; macro audit.

## Verdict
snake_case API, CamelCase variables, typed opaque state, specs on exports. Learning note: `erlang-style-learning-note.md`.
