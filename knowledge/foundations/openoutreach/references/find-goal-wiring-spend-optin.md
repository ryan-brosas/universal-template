<!-- capsule-v2 -->
# Find-command goal wiring — how does a CLI verb turn "a number and a noun" into bounded work without ever spending money the operator didn't ask to spend?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you keep *what to count* independent from *what may be paid for*, and what exactly does exit code 0 mean?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/management/commands/find.py` — `Command.add_arguments` (:70-95), `.handle` (:97-120), `._report` (:124-160), `_announce_the_run` (:174-194), `_select_campaign` (:199-220), `_browser` (:223-239); entry posture `openoutreach/__main__.py:main` (:78-102) + `extract_db_path` (:55-75).
**Signature:** `handle(...)` → `Goal(count, unit)` → `run_job(campaign, goal, on_new_lead=opener, buy_addresses=buy_addresses)`.
**Data Shape:** `count:int`, `unit ∈ {leads, emails}` (default leads), `--emails` flag, `--new`, `--json`, `--open`, `--log-level`/`--debug` sharing one dest.
**Graph evidence:** search_graph "find command goal run job wiring CLI entry main" (153 total; handle/_announce_the_run/__main__.main top hits); job-kernel consumer side (`run_job`, `_work_to_goal`) already owned by the job-goal-bounded-run capsule — this seam is the CLI boundary only.

### Decisive source
```python
        # The unit says what to count; the flag says what may be paid for. A goal counted
        # in addresses cannot be met without buying them, so the noun implies the flag —
        # that is the one place the two are not independent.
        buy_addresses = options["buy_emails"] or options["unit"] == EMAILS
```
And the inversion that motivated it (docstring :16-19):
```python
# This was the other way round until 2026-08-21: buying was on unless ``--no-emails``
# turned it off, so ``find 10 leads`` quietly bought an address for whatever an earlier run
# had left ready. The docstring even called it free. **A flag you forget should cost you a
# feature, never money**, which is the whole argument for the inversion.
```

**Flow:** negative count refused before anything boots → logging/banner configured → ensure_database → ensure_onboarded → validate_operator → campaign selected (`_select_campaign`: named match, or THE only one; ambiguity raises listing the known names — never a guess) → spending posture announced **before any work** ("finding only, no addresses bought" / "buying addresses, one credit each") + ICP echo → `run_job` → `_report` runs whether or not the goal was met (rows to stdout; counts and next-action ask to stderr) → unreached goal then raises typed `GOAL_UNREACHED` carrying produced-of-goal. Entry posture: bare invocation prints OVERVIEW *before Django imports*; `--db PATH` stripped from argv pre-Django because Django parses per-command.
**Invariant:** Exit 0 means the goal was met and nothing else. stdout carries the WHOLE campaign by default (so `> leads.csv` supersedes every earlier file), `--new` narrows to this run's `produced_ids`. Counting leads never authorises a purchase; the only implication direction is unit `emails` ⇒ flag. A silently-no-op flag is a bug: `--open` with no browser fails at argument time, before work.
**Probe:** `tests/test_find.py` whole (382 L) — `test_buying_is_off_by_default` (:212-226, asserts `buy_addresses is False` reaching the cycle), `test_emails_flag_reaches_the_cycle` (:228-235), `test_an_emails_goal_implies_the_flag` (:237-245), `test_an_unreached_goal_still_prints_its_rows_then_exits_non_zero` (:159-171), `test_the_whole_campaign_prints_not_just_this_run` (:173-183) vs `test_new_narrows_to_what_this_run_produced` (:185-193), `test_open_without_a_browser_fails_before_any_work` (:247-255), `test_minute_zero_states_the_goal_and_whether_it_can_spend` (:257-264).
**Coverage:** `check_index_coverage` commands/find.py + tests/test_find.py → no_recorded_issue / metadata_match @ gen 2026-08-25T20:08:16Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "find command goal run_job buy_addresses", limit: 10 });
```

## Verdict
Adopt: count+noun budget grammar with one-direction implication into the spend gate, minute-zero spending announcement, whole-campaign stdout semantics, rows-before-failure reporting, exit-0-means-goal-met. Adapt verbs/flags to your CLI; omit the browser-opener callback and ICP echo if you have no equivalent surfaces.
