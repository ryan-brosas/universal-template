# Learn Bend 2: language and proof workflow

Use for first-time `.bend` implementation or unfamiliar ownership, matching and
proof errors. Bend's Python-shaped syntax is not Python semantics, and Bend 1/HVM
examples are not Bend 2 examples.

## Establish the language version

Run `bend --version`, `bend --help` and `bend guide` for the project's pinned
compiler. Use `bend base --types` or `bend base <name>` for the actual library,
not guessed helpers. The website, current guide and older releases can differ;
resolve a consequential disagreement against the pinned compiler and its source.
Do not upgrade an existing toolchain as a side effect of learning the language.

## Rules that change how you write code

- **Types and reuse:** annotate function parameters, results and arithmetic,
  e.g. `(x + 1 : U32)`. A plain binding is affine: use it at most once. `+x`
  permits reuse of `Data`; `-A` is erased. Closures and arrays are not freely
  copyable. A Bend partial application is an affine closure, not a reusable def.
- **Branching:** match parameters or pattern-bound variables. For a computed
  condition, pass the result to a helper and match its parameter. Observe binder
  order; do not place a let before a match on a parameter. There is no Python
  `if`, and `==` constructs an equality type; runtime equality uses a Base helper
  such as `U32.is_eq`.
- **Recursion:** put the structurally decreasing argument first. Calls must
  preserve earlier arguments until a smaller pattern-derived argument appears.
  Use explicit fuel for externally bounded loops; do not silence a failed
  termination check with `@unsafe` to make a proof pass.
- **Effects:** keep domain rules pure. Use `do IO<T>` with typed `<-` binds for
  effects. Foreign JS/C, files and services need integration tests; a type or
  proof does not establish their real behavior.

## A complete law gate

Create these three files in an isolated directory. This fixture demonstrates
module imports, a universally quantified law and exhaustive proof by cases.
It proves only that two flips restore the input—not every intended property of
an application using the function. Even identity satisfies this law; add
single-step laws or behavioral checks if a flip must actually change its input.

`State.bend`:

```bend
import Base

def flip(value: Bool) -> Bool:
  match value:
    case False{}:
      True{}
    case True{}:
      False{}
```

`LAWS.bend`:

```bend
import Base
import ./State.bend as State

law flip_twice:
  for value: Bool
  {State.flip(State.flip(value)) == value : Bool}
```

`PROOF.bend`:

```bend
import Base
import ./LAWS.bend as Laws

def Laws.flip_twice(value):
  match value:
    case False{}:
      {==}
    case True{}:
      {==}
```

Run `bend PROOF.bend` and require all laws to close. Check the gate itself:

1. Keep the law and proof fixed; change `flip` to return `True{}` in both cases.
   Require an equality/proof failure, not a syntax or missing-tool error.
2. Restore the function; remove `Laws.flip_twice` from the proof file while
   retaining the imports. Require an unproven-law failure.
3. Restore the proof and rerun the positive gate.

Keep requirements in `LAWS.bend` and implementations/proofs elsewhere. Change a
law only for an explicit requirement change, never merely to make checking pass.
For larger proofs, matching refines the goal, recursive proof calls provide
induction, `{==}` closes definitional equality, and `%e : P` rewrites a goal.
`?name` inspects a goal; `?TODO` is unfinished work, not evidence.

If the pinned version documents `--safe`, `bend PROOF.bend --safe` also invokes
the independent BendTT kernel. Inspect its exclusions and translated `.bendtt`
statement: the translation is not proven, foreign implementations are modeled
by type rather than checked, and unsafe definitions remain outside the guarantee.
Do not describe ordinary type checking as this independent check.

## Choose and exercise the execution target

```sh
bend PROOF.bend           # a proof-only file checks without running an app
bend app.bend             # also runs main; not a check-only command
bend app.bend -o app.js   # emit sequential JavaScript
bend app.bend -o app      # build a native executable
```

A pure value-returning `main` is normalized by the checker; do not benchmark that
as native execution. For native parallel work, `a b = f(x) g(y)` forks calls:
balance their costs, not just their syntax. `f!(x)` requests GPU execution on
supporting toolchains. Consult the version's shader guide and build prerequisites;
ship any required `.gpu` companion. Test the actual target: JS stays sequential,
and IO concurrency is not proof of GPU or multicore execution.

For JS/TS deployment and boundary conversion, use
[compiler-free JS deployment](compiler-free-js.md). Never use `--publish` as a
verification step: publishing is an external write, not a local build.

## Sources and verification scope

- [Bend's official introduction](https://bend-lang.com/).
- [Official language guide](https://github.com/bendlang/bend/blob/main/guide/GUIDE.md).
- [Guide revision reviewed](https://github.com/bendlang/bend/blob/af569d4826913b2ce3557e9829ccad31fcf86f94/guide/GUIDE.md).

The guide is the detailed language reference; this note selects the decisions and
failure modes needed to start real work. The fixture was verified with Bend
2.0.7, including both rejection cases, direct boolean behavior and the identity
counterexample. Independent kernel checking and native/JS/GPU artifacts were not
exercised; verify them separately on the consuming project's toolchain.
