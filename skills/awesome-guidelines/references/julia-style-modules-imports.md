<!-- capsule-v2 -->
# Modules and imports — is the package boundary explicit?

**Source:** BlueStyle §Module Imports, Exports, Modules, Global Variables. **Question:** Can maintainers see public API and dependencies at file top?

## Module seam
**Path/Symbol:** main module file and `include` tree.
**Signature:** alphabetical `using`; exports after imports; module wraps entire file.
**Data Shape:** explicit `using Foo: sym` in packages.

### Decisive pattern
```julia
module ExamplePackage

using DataFrames
using Dates: Date, DateTime
using Statistics

export fit_model, predict

const DEFAULT_TOL = 1e-6

function fit_model(data::AbstractMatrix, labels::AbstractVector)
    ...
end

end
```

**Flow:** one `using` package per line, alphabetical → prefer explicit `using Foo: a, b` in packages → group import kinds (modules, types, functions) → exports immediately after imports; theme-group or one per line → avoid globals; if needed uppercase `const MY_VALUE` after exports → module definition occupies whole file (no code before/after); included files don't re-import — parent owns imports → internal helpers prefixed `_`.
**Invariant:** `using A, B`, exports mid-file, mutable globals, or executable code outside module block in library files fails review.
**Probe:** grep `^using .*，`; export placement audit; global `const` scan.

## Extension seam
```julia
using Example

Example.hello(x::Monster) = "Aargh! It's a Monster!"
```

**Flow:** prefer `using` + qualified extension (`Example.hello`) over bare `import` redefinition.
**Invariant:** silent `import Example: hello` then unqualified method add fails BlueStyle extension review.
**Probe:** import style grep; extension location review.

## Verdict
Alphabetical explicit imports, top exports, module-wrapped files, `_` internals. Learning note: `julia-style-learning-note.md`.
