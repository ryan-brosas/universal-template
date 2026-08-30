<!-- capsule-v2 -->
# cli-dead-consent-gate — Which upstream defects surround action execution and reflection wiring in the s3 CLI?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What breaks if you port the s3 CLI loop as written — consent gating, trajectory logging, and the reflection flag?

## Defect seam (erratum capsule)
**Path/Symbol:** `gui_agents/s3/cli_app.py` — `show_permission_dialog` def :133-145 vs sole exec site :215; trajectory key mismatch :219-225; `--enable_reflection` :306-311.
**Signature:** n/a — behavioral audit of the harness loop.
**Data Shape:** run_agent loop: 15 steps max; screenshot → predict → code[0] routed by lowercase substring: done/fail ⇒ dialog+break, "next" ⇒ continue, "wait" ⇒ sleep(5)+continue, else exec(code[0]).

### Decisive source
```python
def show_permission_dialog(code: str, action_description: str):
    """Show a platform-specific permission dialog and return True if approved."""
    ...  # osascript / zenity question dialog
# ...but the execution path NEVER calls it:
            # Ask for permission before executing
            exec(code[0])                    # :215 — comment lies, no gate exists

        if "reflection" in info and "executor_plan" in info:   # :219
            traj += "... Plan:\n" + info["executor_plan"]      # worker returns "plan" (:338), never "executor_plan"

    parser.add_argument("--enable_reflection", action="store_true", default=True, ...)  # :307-309
```

**Flow:** three independent findings, each verified at pin bffdb59c: (1) the consent dialog is defined but unreachable — every grounded action execs WITHOUT user approval despite the comment claiming otherwise (grep shows zero call sites); (2) the trajectory logger tests `"executor_plan" in info` while Worker.generate_next_action emits key `"plan"` (worker.py :337-342) — plans are silently dropped from traj logs; (3) argparse `action="store_true"` with `default=True` makes the flag a no-op — reflection can never be disabled via CLI (only programmatically).
**Invariant:** (1) Any port that assumes consent gating exists because a helper is present is WRONG — add the call before exec or drop the pretense. (2) Cross-module dict keys are untyped contracts; the executor_info producer and consumer drifted. (3) store_true + default=True cannot express "default on, flag turns it off" — needs BooleanOptionalAction or inverse flag.
**Probe:** `grep -c 'show_permission_dialog' gui_agents/s3/cli_app.py` → 1 (the def line only; zero call sites).
**Probe:** `grep -n 'executor_plan\|"plan":' gui_agents/s3/cli_app.py gui_agents/s3/agents/worker.py` → cli :219/:224 vs worker :338 — the mismatch pair.
**Probe:** `grep -n -A2 '"--enable_reflection"' gui_agents/s3/cli_app.py` → store_true with default=True.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "s3 cli_app main argparse AgentS3", limit: 5 });
```

## Verdict
Adopt nothing blindly here: this capsule is a porting-hazard map. Fix all three at port time (wire the dialog or remove it; align the info key; replace the flag). Evidence is grep-pinned at bffdb59c; re-verify against your base commit before citing as still-open upstream.
