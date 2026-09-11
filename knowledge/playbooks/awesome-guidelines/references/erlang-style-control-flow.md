<!-- capsule-v2 -->
# Control flow — are branches pattern-matched and errors isolated?

**Source:** Inaka §Syntax; OTP LNG-002. **Question:** Is control flow explicit without `if`, legacy `catch`, or spaghetti nesting?

## Clause seam
**Path/Symbol:** function bodies with branching logic.
**Signature:** pattern-matching clauses; ≤3 nesting levels; no `if`.
**Data Shape:** small single-purpose functions (~12 expressions).

### Decisive pattern
```erlang
process_payment(authorized, State) ->
    capture_funds(State);
process_payment(declined, State) ->
    {error, declined, State};
process_payment(pending, State) ->
    schedule_retry(State).

filter_users([]) ->
    [];
filter_users([#user{active = true} = U | Rest]) ->
    [U | filter_users(Rest)];
filter_users([_ | Rest]) ->
    filter_users(Rest).
```

**Flow:** replace top-level `case` with function clauses when each branch is substantial → avoid `if` — use `case` or clauses → nest at most ~3 levels → split with tail-recursive helper (`continue_foo/1`) to reset indent → prefer list comprehensions/folds over error-prone manual recursion → use iolists not `++` for IO building.
**Invariant:** `if`, list comprehension with inner `case`, or 30-line nested `begin` fails review.
**Probe:** grep `\bif\b`; nesting depth review; function expression count.

## Error seam
```erlang
case file:read_file(Path) of
    {ok, Bin} ->
        parse(Bin);
    {error, Reason} ->
        {error, Reason}
end.

try file:read_file(Path) of
    Bin -> parse(Bin)
catch
    error:Reason -> {error, Reason}
end.
```

**Flow:** golden path separate from errors — `try … of … catch`, never `case catch` or legacy `catch` → avoid `throw` for non-local returns unless deep recursion escape hatch → don't nest `try…catch` blocks.
**Invariant:** `case catch`, bare `catch`, or nested try/catch fails review.
**Probe:** grep `case catch` and legacy `catch` token; xref for throw usage.

## Verdict
Clause functions, no if, shallow nesting, modern try/of/catch. Learning note: `erlang-style-learning-note.md`.
