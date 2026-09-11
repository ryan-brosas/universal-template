<!-- capsule-v2 -->
# Naming and files — do identifiers and paths read as English GNU symbols?

**Source:** GNU Coding Standards §Naming Variables, Functions, and Files. **Question:** Are globals/functions descriptive lowercase_with_underscores, flags named by meaning, and paths portable?

## Identifier seam
**Path/Symbol:** functions, globals, macros, enums across GNU C sources.
**Signature:** `ignore_space_change_flag` not `iCantReadThis`; macros/enums UPPER_CASE.
**Data Shape:** English words; underscores between words; limited abbreviations.

### Decisive pattern
```c
/* Ignore changes in horizontal whitespace (-b).  */
int ignore_space_change_flag;

enum { READ_ONLY = 1, READ_WRITE = 2 };
```

**Flow:** treat global names as documentation — prefer informative English over terseness → use lowercase with underscores between words so Emacs word commands work → reserve UPPER_CASE for macros and enum constants (and uniform prefix conventions) → local names may be shorter when single-function scope and comments clarify → limit obscure abbreviations; document any abbrev set you reuse → for CLI option storage, name variables after option **meaning**, comment both meaning and letter → prefer `enum` for named integer constants over `#define` when appropriate → avoid CamelCase/mixedCase identifiers.
**Invariant:** terse or camelCase global like `iCantReadThis` or flag variable named only `b_flag` without semantic name fails GNU naming review.
**Probe:** review new public symbols; grep for `[a-z][A-Z]` in identifiers; flag vars vs `getopt_long` option list.

## File naming seam
**Flow:** use lowercase file names → run `doschk` when targeting hostile short-name filesystems (legacy GNU packages may keep ≤14 char names — preserve if already present; not required for new programs) → keep file names meaningful and collision-aware across the package.
**Invariant:** thoughtless long names that break target FS constraints fail portability check when package claims that support.
**Probe:** `doschk` on added paths when package documents FS portability; review rename impact.

## Verdict
Descriptive lowercase_with_underscores, semantic CLI flag names, enum constants, portable file names. Learning note: `gnu-style-learning-note.md`.
