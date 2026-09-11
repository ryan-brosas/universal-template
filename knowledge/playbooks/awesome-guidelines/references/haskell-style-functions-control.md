<!-- capsule-v2 -->
# Functions and control — are functions short, typed, and total?

**Source:** HaskellWiki §Good Programming Practice; Tibbe §If/case/Point-free/Warnings. **Question:** Will `-Wall` and readers catch misuse before runtime?

## Function seam
**Path/Symbol:** top-level and local function definitions.
**Signature:** type signature on exports; guards over if; avoid partial primitives.
**Data Shape:** small composable bodies using `$` / `.`.

### Decisive pattern
```haskell
lookupUser :: Map UserId User -> UserId -> Maybe User
lookupUser users uid =
    Map.lookup uid users

parseHeader :: ByteString -> Either ParseError Header
parseHeader bytes =
    case BS.splitOn "\r\n" bytes of
        (line : _) | not (BS.null line) -> decodeLine line
        _                               -> Left EmptyHeader

sumStrict :: [Int] -> Int
sumStrict = go 0
  where
    go !acc []    = acc
    go acc (x:xs) = go (acc + x) xs
```

**Flow:** keep functions a few lines — decompose large `case` on big ADTs → type signature on every top-level/exported function → prefer guards/patterns over `if-then-else` → replace partial `head`/`fromJust` with `case`/`maybe` and documented errors → short list comps only; prefer `map`/`filter`/`foldr` → use `$` and `.` to reduce parens (spaces around `$`) → point-free only when still readable → compile with `-Wall -Werror`; no unused/shadowing/non-exhaustive patterns.
**Invariant:** bare `head`, missing top-level sig on export, or warning-suppressed overlap fails review.
**Probe:** GHC `-Wall`; HLint partial rule; function length spot check.

## Error seam
```haskell
-- prefer
maybe (error "Module.fn: missing key") id (Map.lookup k m)

-- over bare head on unknown list
```

**Flow:** `error` strings fixed and grep-friendly; don't rely on partial patterns for expected failures.
**Invariant:** partial function on untrusted input without prior proof fails review.
**Probe:** HLint `Use maybe`; partial function grep.

## Verdict
Typed short functions, total patterns, HLint/GHC-clean control flow. Learning note: `haskell-style-learning-note.md`.
