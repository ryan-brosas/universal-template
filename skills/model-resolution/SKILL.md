---
name: model-resolution
description: "Use when execution-router has already chosen a role and mechanism and the lane needs a concrete backend/model: discover available providers and models at runtime, hard-filter by the role's capabilities, rank by local preference, and fall back gracefully."
disable-model-invocation: true
---

# Model Resolution (internal)

**ROLE → REQUIRED CAPABILITY → BEST CURRENTLY AVAILABLE MODEL.** Never
MODEL → WORKFLOW. Providers and models are runtime state: discover what exists
now, filter by the role's hard requirements, rank with local preferences,
degrade gracefully. Prefer the mechanical resolver; read this skill only when
the resolver is absent or its result needs adjudication.

## Mechanical path (default)

```bash
python3 ~/.agents/scripts/resolve-model.py --role reviewer --json
python3 ~/.agents/scripts/resolve-model.py --role worker --require-context 128000 --json
```

The resolver discovers (`pi --list-models`, `veda models`, `which`), applies
the role's hard filters (backend present, model in catalog, context ≥ required,
capability flags, auth where checkable), ranks survivors by
`config/model-profiles.yaml` preference order, and prints candidates plus
excluded reasons as JSON. Read its output; do not re-derive it by hand.

## Role → capability requirements

| Role | Requires |
|---|---|
| MAIN | economical, fast, tool-capable, holds the session |
| WORKER | code competence, write access in its slice, cheap |
| REFERENCE-INVESTIGATOR | code comprehension, adequate context, read-only, cheap |
| REVIEWER | strong reasoning, read-only, independent context, high confidence |
| NAVIGATOR | strong planning reasoning, read-only, structured output |
| FRONTEND-CRITIC | UI/UX or multimodal reasoning ability — whichever available model has it |
| DEBUGGER | runtime/tool access, hypothesis discipline |
| SECURITY-REVIEWER | adversarial reasoning, read-only |
| SOLVER / JUDGE / VERIFIER | independent strong reasoning; diversity between them when the problem is hard |
| SUPERVISOR | orchestration reliability, budget discipline |

## Runtime discovery (re-verify per installed version)

| Question | Command |
|---|---|
| Pi providers/models (context, thinking, images) | `pi --list-models [search]` |
| Pi provider readiness | `pi auth check --provider <name>` (environment-scoped) |
| Veda backends/aliases | `veda models [backend]` |
| Veda personas | `veda personas` |
| Backend CLIs present | `which claude codex droid gemini agy` |
| Full stack report | `python3 ~/.agents/scripts/runtime-capabilities.py [--json] [--smoke [backend]]` |

## Addressing (verified mechanics; re-verify per version)

- Pi models via the Veda Pi backend are addressed **`pi/<provider>/<model>`**;
  strings without the `pi/` prefix are rejected. The Veda Pi backend may not
  enumerate Pi's catalog — discover with `pi --list-models`, pass an explicit
  `pi/...` model, and one-shot probe unfamiliar lanes.
- Direct backends: `veda -b <backend> -m <model>`. When the model is omitted
  Veda picks its own backend default, which may be invalid — always pass an
  explicit backend-appropriate model per lane.
- `veda -b pi` bridges to whatever Pi has configured, so new Pi providers
  become usable lanes automatically.
- Installed ≠ authenticated: a backend CLI can be present yet unauthenticated,
  and readiness checks are environment-scoped — verify in the environment the
  lane will run in.

## Stable preferences vs runtime state

- `config/model-profiles.yaml` (git-tracked): **stable preference chains
  only** — which models are preferred per role. No auth state, no dated quirks.
- Runtime observations (auth state, broken flags, dated quirks): generated
  state under `state/` (gitignored) or the resolver's live discovery. Record
  quirks in the task's audit note, not in tracked config.

## Fallback rules

- **Infrastructure failure** (provider down, auth expired, CLI missing): mark
  unavailable for this task, take the next compatible candidate, or fall back
  to Main's model with the same role requirements. Never fail the task.
- **Weak answer** (wrong result, hallucination, shallow reasoning): do not
  blind-retry the same lane — escalate the capability requirement and
  re-resolve (stronger or different model), or do the step yourself with
  ground truth.
- One fallback per attempt; no retry storms.
- Diversity is for correlated-failure reduction or genuinely different
  capability — never ceremony. Same provider, different models is valid.

## Verification

Resolution is traceable: role → requirements → discovery output → filtered/
ranked choice → fallback used (if any). A one-shot probe verifies an
unfamiliar lane before real work.

## References

- `../execution-router/SKILL.md` — chooses the mechanism and role this skill resolves
- `../veda-lane/SKILL.md` — executing through Veda once a Veda lane is selected
- `../../config/model-profiles.yaml` — stable preference chains
- `../../scripts/resolve-model.py` — the mechanical resolver
