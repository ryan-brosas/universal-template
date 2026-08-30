<!-- capsule-v2 -->
# Naming and modules — are names descriptive and modules focused?

**Source:** Elm official style guide; Elm Guide Modules; NoRedInk guide. **Question:** Can readers trace symbols and module boundaries without guesswork?

## Naming seam
**Path/Symbol:** functions, types, imports in Elm packages.
**Signature:** descriptive names; qualified imports by default.
**Data Shape:** one central custom type per module.

### Decisive pattern
```elm
module Post exposing (Post, decoder, encode, estimatedReadTime)

import Json.Decode as Decode
import Json.Encode as Encode
import String


type Post
    = Post
        { title : String
        , body : String
        }


estimatedReadTime : Post -> Int
estimatedReadTime (Post record) =
    String.words record.body
        |> List.length
        |> (\wordCount -> wordCount // 200)
```

**Flow:** long descriptive names beat abbreviations → qualify calls (`String.words`, not unqualified `words`) → module organized around `Post` type → expose only public API → file `src/Post.elm` for `module Post`.
**Invariant:** `accdns`-style abbreviations, `import List exposing (map)` everywhere, or `Todo.Todo` repetitive namespace fails review.
**Probe:** import audit; public `exposing` list matches API review.

## Import seam
```elm
import Html exposing (Html, div, text)
import Html.Attributes as Attr

import Post
-- use Post.Post, Post.encode, etc.
```

**Flow:** default to qualified imports → `exposing (..)` rarely (Html exception) → prefer `import X as Alias` for long module names.
**Invariant:** multiple modules with `exposing (..)` causing ambiguous `map`/`filter` fails review.
**Probe:** grep `exposing (..)` count; compiler ambiguous name errors.

## Verdict
Descriptive qualified names, focused modules, minimal exposing. Learning note: `elm-style-learning-note.md`.
