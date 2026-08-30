<!-- capsule-v2 -->
# Slash-command soft dispatch — how do you make `/<skill> args` reach the planner WITHOUT forging turns or hard-executing?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What is the dispatch ladder for a slash invocation, and why does a recognized skill produce planner *suggestion text* instead of executing?

## parse → registry lookup → three-kind result
**Path/Symbol:** `src/cuga/backend/slash_commands/parser.py:14-40` (`parse` + `_SLASH_RE`), `dispatcher.py:44-104` (`parse_and_dispatch`, `_dispatch_parsed`).
**Signature:** `parse(raw: str | None) -> ParsedSlash | None`; `async parse_and_dispatch(raw, *, slash_registry, skill_registry=None, thread_id=None, clear_stop_event=None, extra=None) -> DispatchResult`.
**Data Shape:** `ParsedSlash(name, raw_args, raw_input)`; `DispatchResult(kind: "skill"|"passthrough"|"unknown", planner_input?, resolved_name?, raw_input?, raw_args?)`.

### Decisive source
```python
# parser.py — slash is reserved for explicit user-side dispatch
_SLASH_RE = re.compile(r"^/([a-zA-Z0-9_][a-zA-Z0-9_:-]*)(?:\s+(.*))?$", re.DOTALL)
# Empty "/", leading whitespace before "/", or slash not at position 0
# all return None = "pass through to the planner as plain text".
```
Dispatch is KIND-BASED (dispatcher.py:71-89): builtins would hard-dispatch (run here, never reach the planner), but skills SOFT-SUGGEST — a hit returns `kind="skill"` with `planner_input=translate_skill_invocation(name, args)`. Translation (translation.py:24-33): `"use the skill named '<name>' to: <raw_args>"` (short form without args). The planner then decides to call `load_skill` itself — the tool already lives in the CodeAct exec namespace and skills are discoverable via the `<available_skills>` prompt block, so no forged conversation turns are needed. The same entry is called from BOTH the FastAPI `event_stream` and SDK `CugaAgent.invoke` so both surfaces get identical semantics.

**Flow:** raw input → `parse()` (None ⇒ passthrough with `raw_input`) → `slash_registry.has_skill(name)` (registry rebuilt per request so new SKILL.md files appear without restart) → skill: translated suggestion + original preserved for display/history; unknown: caller may fall back to the planner or surface an error. Every recognized invocation emits telemetry with SHAPE metadata only (`args_length`, never raw strings — they may carry secrets/PII).
**Invariant:** Slash dispatch never fabricates agent history; it converts an explicit user hint into plain input and lets the planner own the decision. Telemetry must not break dispatch and must not log raw user args.

**Probe:** `tests/unit/test_slash_message_synthesis.py::test_dispatcher_populates_planner_input_for_known_skill / test_dispatcher_unknown_slash_has_no_planner_input / test_translation_preserves_args_verbatim_including_quotes_and_newlines` + `tests/unit/test_slash_langfuse_span.py::test_langfuse_exception_is_swallowed` — pin dispatch kinds, verbatim arg transport, and telemetry-never-breaks-dispatch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "parse_and_dispatch DispatchResult translate_skill_invocation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the soft-suggest ladder (parse-at-position-zero, kind-based dispatch, translated suggestion preserving raw input) and the shape-only telemetry rule. Adapt command kinds to your surface. Omit builtin hard-dispatch until you have one. Direct tests exist for dispatch and translation.
