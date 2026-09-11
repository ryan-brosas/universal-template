<!-- capsule-v2 -->
# Types and IO — are data models explicit and effects separated?

**Source:** HaskellWiki §Types/I/O/Records; Tibbe §laziness. **Question:** Will strictness and module boundaries prevent space leaks and IO surprises?

## Type seam
**Path/Symbol:** algebraic types, records, IO modules.
**Signature:** `data`/`newtype` over synonyms; strict fields; pure/IO split.
**Data Shape:** strict accumulators where needed.

### Decisive pattern
```haskell
newtype UserId = UserId { unUserId :: Text }
    deriving (Eq, Ord, Show)

data Point = Point
    { pointX :: !Double
    , pointY :: !Double
    }
    deriving (Eq, Show)

runRequest :: HttpClient -> Request -> IO Response
runRequest client req = do
    let path = requestPath req
    body <- fetch client path
    pure (decodeResponse body)
```

**Flow:** prefer proper `data`/`newtype` to type synonyms and bare tuples for domain concepts → no class constraints on `data` declarations → factor repeated variant fields out of ADTs → record updates: build new values; mind polymorphic field pitfalls → strict constructor fields (`!`) by default; lazy function parameters unless strict accumulator (`go !acc`) → separate pure logic modules from IO modules → in `do`, use `let` not `<- return` → avoid lazy read+write same handle; no production `trace` for users → use `Text`/`ByteString` instead of `String` in new APIs.
**Invariant:** lazy record fields everywhere, mixed pure/IO in one undifferentiated module, or `String` wire types in new library code fails review.
**Probe:** strict field audit; module dependency graph (IO imports only at edges); grep `String` in public API types.

## Records seam
**Flow:** avoid exposing large record constructors directly when field set may evolve — use smart constructors or pattern exports.
**Invariant:** client code tied to record ctor order without abstraction fails evolution review.
**Probe:** export list vs direct `{ field = … }` usage across package boundary.

## Verdict
newtype/data models, strict fields, IO at boundaries, no lazy IO footguns. Learning note: `haskell-style-learning-note.md`.
