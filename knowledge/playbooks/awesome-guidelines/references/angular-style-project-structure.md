<!-- capsule-v2 -->
# Project structure — is UI under src/, bootstrapped from main.ts, and organized by feature?

**Source:** Angular Style Guide §Project structure. **Question:** Does the repo layout match 2025 feature-first Angular conventions?

## Structure seam
**Path/Symbol:** Angular application repository tree.
**Signature:** `src/main.ts`; feature subdirs; one concept per file.
**Data Shape:** `src/movie-reel/show-times/film-details/` not `src/components/`.

### Decisive pattern
```
src/
  main.ts
  movie-reel/
    show-times/
      film-calendar/
      film-details/
    reserve-tickets/
      payment-info/
```

**Flow:** all Angular UI (TS/HTML/styles) lives in **`src/`** — config/scripts outside → bootstrap only in **`src/main.ts`** → group **component ts + template + styles + spec** in **same directory** → organize by **feature area**, not by type — **avoid** top-level `components/`, `directives/`, `services/` buckets → split directories when file count hurts navigation → **one concept per file** (one component/directive/service; tiny related group OK) → prefer **smaller files** when unsure.
**Invariant:** type-based folder layout or bootstrap outside `main.ts` fails structure review.
**Probe:** tree walk — no `src/services` monolith; `main.ts` at `src/` root.

## Verdict
Feature-first `src/` layout with colocated artifacts and focused files. Learning note: `angular-style-learning-note.md`.
