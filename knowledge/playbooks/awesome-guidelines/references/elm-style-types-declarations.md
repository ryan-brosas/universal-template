<!-- capsule-v2 -->
# Types and declarations — are unions and domain IDs compiler-safe?

**Source:** Elm official style guide §Types; NoRedInk §Identifiers. **Question:** Will type changes produce meaningful diffs and catch ID mixups?

## Type layout seam
**Path/Symbol:** custom types and type aliases in Elm modules.
**Signature:** simple per-line constructors/fields; custom types for nominal IDs.
**Data Shape:** exhaustive case expressions.

### Decisive pattern
```elm
type Boolean
    = Literal Bool
    | Not Boolean
    | And Boolean Boolean
    | Or Boolean Boolean


type alias Circle =
    { x : Float
    , y : Float
    , radius : Float
    }


type StudentId
    = StudentId String
```

**Flow:** union constructors each on own line with simple indent → record aliases one field per line (no column-alignment padding) → use custom type wrappers for domain IDs, not `type alias StudentId = String` → `case` covers all constructors when type may grow.
**Invariant:** horizontally aligned `|` columns, `type alias` for IDs, or default `_ ->` catch-all on extensible union fails review.
**Probe:** compiler exhaustiveness; code review on new constructors.

## Decoder co-location seam
```elm
type alias User =
    { name : String
    , displayName : String
    }


decoder : Decoder User
decoder =
    Decode.map2 User
        (Decode.field "name" Decode.string)
        (Decode.field "displayName" Decode.string)
```

**Flow:** keep decoder beside the type it decodes → field order changes stay visible in one diff hunk.
**Invariant:** decoder in separate module from its record type without strong reason fails review.
**Probe:** pair grep `type alias User` with `decoder : Decoder User` in same file.

## Verdict
Simple union/alias layout, custom ID types, exhaustive case, co-located decoders. Learning note: `elm-style-learning-note.md`.
