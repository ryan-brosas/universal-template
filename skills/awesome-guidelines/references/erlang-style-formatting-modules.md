<!-- capsule-v2 -->
# Formatting and modules — is layout readable and module structure coherent?

**Source:** Inaka erlang_guidelines §Source Code Layout. **Question:** Can reviewers scan exports, types, and functions without fighting indentation?

## Layout seam
**Path/Symbol:** `src/**/*.erl` application modules.
**Signature:** 2-space indent; ≤100 columns; types and records before functions.
**Data Shape:** exported functions grouped before private helpers.

### Decisive pattern
```erlang
-module(user_repo).
-behaviour(gen_server).

-export([start_link/0, fetch/1]).

-type user_id() :: binary().
-type state() :: #user_repo_state{}.

-record(user_repo_state, {conn :: pid()}).

-spec fetch(user_id()) -> {ok, map()} | {error, not_found}.
fetch(Id) when is_binary(Id) ->
    gen_server:call(?MODULE, {fetch, Id}).

handle_call({fetch, Id}, _From, State) ->
    {reply, do_fetch(Id, State), State}.
```

**Flow:** spaces not tabs, 2-space indent → surround operators/commas with spaces → max ~100 columns → place `-type` and records at module top → group exported functions first (unless readability dictates otherwise) → prefer clause heads over a top-level `case` → no god modules; split by subdirectory when many modules.
**Invariant:** tabs, trailing whitespace, types buried mid-file, or 6000-line god module fails review.
**Probe:** `whitespace` scan; module line count; exported/private grouping review.

## Header seam
**Flow:** `.hrl` files hold macros only (if any) — no types, records, or function definitions → records stay in owning module with opaque export when shared.
**Invariant:** shared record in `.hrl` or types in include files fails review.
**Probe:** grep `-record` / `-type` in `include/*.hrl`.

## Verdict
2-space layout, types/records first, grouped exports, no shared record headers. Learning note: `erlang-style-learning-note.md`.
