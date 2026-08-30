<!-- capsule-v2 -->
# Comments and verification — is non-obvious code explained and build-clean?

**Source:** Apache httpd style guide intro + comment examples; generic C safety baseline. **Question:** Do comments document rationale and do httpd builds/tests pass?

## Comment seam
**Path/Symbol:** httpd patches and module C sources.
**Signature:** comments at code indent; rationale for non-obvious logic.
**Data Shape:** function behavior notes where code alone is insufficient.

### Decisive pattern
```c
code;
/* Explain why this edge case exists, not what the next line does. */
code;
```

**Flow:** comment code whose purpose is not obvious from reading alone → document function behavior and rationale where needed → indent comments to the same level as surrounding statements → prefer explaining why over restating what → pair httpd layout rules with generic C safety from `c-coding-practices`: initialize variables, check error returns, keep headers declaration-only unless httpd tree conventions say otherwise → verify changes with project build (`./buildconf` / `make` per tree docs) and tests relevant to touched modules → optionally reformat with GNU indent httpd flags before review; whitespace-only reformats in separate commits.
**Invariant:** misleading comment, missing rationale on tricky control flow, or unchecked error path fails review even when layout matches.
**Probe:** comment-on-non-obvious-block checklist; build/test CI on changed module.

## Verify seam
**Flow:** `-Wall -Wextra` (or httpd tree flags); module test suite when available.
**Invariant:** compiler warning regression on touched files without fix or documented waiver fails verify gate.
**Probe:** build log for changed paths.

## Verdict
Indented rationale comments plus httpd build and generic C safety checks. Learning note: `httpd-style-learning-note.md`.
