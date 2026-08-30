<!-- capsule-v2 -->
# Modules and types — are responsibilities encapsulated and evolvable?

**Source:** Microsoft guidelines §Object/Type/Module design; Union Types. **Question:** Can the representation evolve without breaking callers?

## Organization seam
**Path/Symbol:** library modules, classes, interfaces, discriminated unions.
**Signature:** namespace or module per file; hide record/union representation when unstable.
**Data Shape:** interfaces for operation groups; DUs for tree data.

### Decisive pattern
```fsharp
namespace Fabrikam.Collections

type BinaryTree<'T> =
    private
    | Empty
    | Node of 'T * BinaryTree<'T> * BinaryTree<'T>

type BinaryTree<'T> with
    member tree.Contains value =
        match tree with
        | Empty -> false
        | Node (v, left, right) ->
            value = v || left.Contains value || right.Contains value

    static member Empty = Empty
    static member Singleton x = Node (x, Empty, Empty)
```

**Flow:** start file with `namespace` or top-level `module` → put intrinsic behavior on the type as methods/properties → encapsulate mutable state in classes with private fields → group related ops in interfaces (not records of functions) → use DUs for recursive/tree structures → mark record/union cases `private` or hide in `.fsi` when design may change → prefer interface implementation over inheritance hierarchies → custom modules extending `List`/`Seq`/`Array` get `[<RequireQualifiedAccess>]`.
**Invariant:** public exposed record fields on evolving types, inheritance-based extensibility, or unqualified shadowing module without `RequireQualifiedAccess` fails review.
**Probe:** API review for public case exposure; grep `[<RequireQualifiedAccess>]` on extension modules.

## Operator seam
**Flow:** publish named members first; add symbolic operators only when notation benefit outweighs doc cost → use static members on domain types (e.g. `Vector`) when operators are natural.
**Invariant:** public custom symbolic operators without named equivalent fails review.
**Probe:** public API grep for `( + )`, `( .* )`, etc.

## Verdict
Hidden representations, interfaces/DUs, qualified modules, minimal inheritance. Learning note: `fsharp-style-learning-note.md`.
