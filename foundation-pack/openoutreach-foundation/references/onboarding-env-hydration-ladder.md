<!-- capsule-v2 -->
# Onboarding env hydration ladder — how does a wizard-shaped setup also complete headless, and when does a bad env value stop the run instead of being skipped?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you give an agent-driven (TTY-less) install the same onboarding as a human without half-applying state or inferring consent?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/onboarding.py` — `OnboardingEnvError` (:121-130), `_env`/`_env_bool`/`_env_validated` (:133-155), `Step` (:162-176), `_llm_from_env` (:277-297), `_account_from_env` (:405-421), `STEPS` (:518-535), `hydrate_from_env` (:543-554), `missing_env_keys`/`env_help` (:557-568); consumer `core/management/bootstrap.py:ensure_onboarded` (:38-71).
**Signature:** `hydrate_from_env() -> set[str]` (keys filled); `missing_keys() -> set[str]`; `env_help() -> str`.
**Data Shape:** every variable prefixed `OPENOUTREACH_`; each `Step(key, is_done, run, from_env, env_keys)` owns its own fields; `from_env` returns whether it hydrated.
**Graph evidence:** search_graph "onboarding steps wizard env save llm questionary" (112 total); get_code_snippet `hydrate_from_env`; trace inbound = `bootstrap.ensure_onboarded` + `commands/find.handle` + `commands/init.handle`.

### Decisive source
```python
class OnboardingEnvError(SystemExit):
    """Raised when a variable is set but unusable — never silently ignored.

    A bad value is a different thing from an absent one: absent means *ask*, bad
    means *stop and say so*. Falling through to "missing" would print a variable
    the operator has already set."""
```
And the hydration loop:
```python
    for step in STEPS:
        if not step.is_done() and step.from_env():
            filled.add(step.key)
```

**Flow:** `ensure_onboarded`: already-complete ⇒ return → hydrate in STEPS order (campaign → llm live-verified → bettercontact key → account) so a later step can rely on an earlier row → still missing + TTY ⇒ interactive wizard → still missing headless ⇒ typed `ONBOARDING_INCOMPLETE` whose message **names the variables** (`env_help()`), never a bare "incomplete". Each step is all-or-nothing: `_campaign_from_env` returns False unless BOTH fields are present ("a half-filled step would persist state the wizard would then have to reconcile").
**Invariant:** Absent ≠ invalid: absent fields leave the step unsatisfied (ask later); a set-but-wrong value raises `OnboardingEnvError` naming the exact variable (test: `"XX"` country stops the whole run). Acceptance is never inferred — `ACCEPT_LEGAL_NOTICE` must literally say yes or the account step stays open; newsletter defaults off under env everywhere because "silence in a config file is not consent" (the jurisdiction-aware ON default is a suggestion to a human only). The LLM step verifies credentials at boot exactly as the wizard does — "there is nobody to re-ask, and the daemon would fail later inside a qualification instead of at boot".
**Probe:** `tests/test_onboarding.py` whole (282 L) — `test_full_environment_completes_onboarding_without_a_prompt` (:202-210), `test_partial_environment_leaves_the_rest_missing` (:214-224, no Campaign row created), `test_legal_acceptance_is_never_inferred` (:241-248), `test_newsletter_defaults_off_when_unset` (:252-257), `test_bad_country_stops_rather_than_asking_for_it_again` (:261-266), `test_unverifiable_llm_key_stops_at_boot` (:270-276); boot ladder locked in `tests/test_find.py:69-106` (`test_headless_and_unconfigured_names_the_variables`, `test_a_tty_still_gets_the_wizard`).
**Coverage:** `check_index_coverage` core/onboarding.py, tests/test_onboarding.py, core/management/bootstrap.py → no_recorded_issue / metadata_match @ gen 2026-08-25T20:08:16Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "hydrate_from_env onboarding steps env", limit: 10 });
```

## Verdict
Adopt: steps that own (done-check, runner, env path, env keys) for the same fields; ordered all-or-nothing hydration; absent-ask vs set-but-bad-stop vocabulary; explicit-consent-only gates; headless exit text that names the variables. Adapt the step list and prefix to your product; omit the Django User creation and hub-token mint (product plumbing).
