<!-- capsule-v2 -->
# Naming and types — are identifiers guessable and type shapes consistent?

**Source:** NEP-1 §Naming Conventions. **Question:** Can a reader predict proc names and distinguish value/ref/error types?

## Type seam
**Path/Symbol:** exported types, enums, constants in modules.
**Signature:** PascalCase types; camelCase vars/procs; Error/Defect suffixes; Ref/Ptr/Obj suffixes.
**Data Shape:** `initFoo` vs `newFoo`; prefixed enum members unless `{.pure.}`.

### Decisive pattern
```nim
const aConstant = 42

type
  Handle = object
    fd: int64
  HandleRef = ref Handle

  ValueError* = object of CatchableError

  PathComponent = enum
    pcDir
    pcLinkToDir
    pcFile

  PathComponentPure {.pure.} = enum
    Dir
    LinkToDir
    File

proc initHandle(): Handle =
  Handle(fd: -1)

proc newHandleRef(): HandleRef =
  HandleRef(fd: -1)
```

**Flow:** PascalCase type names; camelCase for procs/vars (vars start lowercase) → constants camelCase or PascalCase; avoid ALL_CAPS except ugly C wrappers → most-used variety gets plain name; add `Obj`/`Ref`/`Ptr` to less common shapes → exception types end in `Error` or `Defect`; inherit `CatchableError`/`Defect` not bare `Exception` → non-`{.pure.}` enums prefix members (`pcDir`); pure enums use PascalCase members → use `initFoo` for value init, `newFoo` for ref/ref-semantics → treat acronyms as words (`parseUrl`, not `parseURL`) → mutating views prefix `m` (`mitems`) → copy variant past participle (`sorted` vs `sort`); in-place add `-In` when copy exists.
**Invariant:** shouting acronyms, unprefixed impure enum literals, or generic `Foo of Exception` fails stdlib-style review.
**Probe:** `--styleCheck:error`; enum prefix audit; init/new naming grep.

## API vocabulary seam
**Flow:** subjectVerb not verbSubject (`fileExists` not `existsFile`) → abbrev table for stdlib-shaped names: `len` not `getLen`, `add` not `append`, `find` returns index, `contains` bool, `cmp` tri-state int, `del` unordered fast delete vs `delete` stable.
**Invariant:** `getLen`, `append`, or `existsFile` in new API surface fails consistency review.
**Probe:** naming vocabulary checklist against NEP-1 abbrev table.

## Verdict
PascalCase/camelCase discipline, typed variants, guessable abbreviated API names. Learning note: `nim-style-learning-note.md`.
