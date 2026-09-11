<!-- capsule-v2 -->
# Pipelines and expressions — are transforms and helpers idiomatic?

**Source:** Elm official + NoRedInk style guides. **Question:** Are pipelines multi-step and large lets factored out?

## Pipeline seam
**Path/Symbol:** data transformation expressions.
**Signature:** `|>` only for multi-step chains; subject leftmost.
**Data Shape:** parens preferred over `<|`.

### Decisive pattern
```elm
sanitizeTitle : String -> String
sanitizeTitle raw =
    raw
        |> String.trim
        |> String.toLower


viewPromptAndPassagesAccordions : Model -> Html Msg
viewPromptAndPassagesAccordions model =
    div []
        [ viewHeader model
        , viewBody model
        ]


Maybe.map (\_ -> ()) maybeValue
```

**Flow:** use `|>` when ≥2 transformations with data first → otherwise direct call `List.map f list` → prefer parentheses nesting over `<|` chains → use `\_ ->` instead of `always` → split giant `let` into top-level named functions (with type annotations).
**Invariant:** single-step `list |> List.map f`, `<|`-heavy application, or 30-line `let` block fails review.
**Probe:** Credo-style manual review / elm-review rules for pipelines and let size.

## Case layout seam
```elm
animalToString : Animal -> String
animalToString animal =
    case animal of
        Dog ->
            "dog"

        Cat ->
            "cat"
```

**Flow:** `case` keyword introduces branches clearly → each branch body indented consistently → avoid cramming branches on same line as arrow when complexity grows.
**Invariant:** `_` wildcard on union expected to gain constructors fails review.
**Probe:** exhaustiveness compiler warning enabled.

## Verdict
Multi-step pipes, factored lets, parens over <|, exhaustive case. Learning note: `elm-style-learning-note.md`.
