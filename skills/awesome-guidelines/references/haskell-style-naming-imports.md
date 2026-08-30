<!-- capsule-v2 -->
# Naming and imports — are symbols descriptive and imports explicit?

**Source:** HaskellWiki §Naming/Imports; Tibbe §Imports/Naming. **Question:** Can Haddock and grep navigate the module graph safely?

## Naming seam
**Path/Symbol:** modules, exports, import lists.
**Signature:** lowerCamelCase functions; UpperCamelCase types; Haddock header.
**Data Shape:** grouped explicit imports.

### Decisive pattern
```haskell
{-|
Module      :  Network.Client.Http
Description :  Minimal HTTP client helpers
Copyright   :  (c) 2026 Example Corp
License     :  BSD-3-Clause
Maintainer  :  dev@example.com
Stability   :  experimental
-}

module Network.Client.Http
    ( HttpClient
    , newClient
    , getJson
    ) where

import Control.Monad.IO.Class (MonadIO, liftIO)
import Data.Text (Text)
import qualified Data.Map as Map
import qualified Data.Set as Set
```

**Flow:** Haddock module header with Maintainer/Stability → descriptive camelCase identifiers; UpperCamelCase for types/constructors → avoid gratuitous symbolic infix in app code → singular module names → imports grouped: stdlib, third-party, local — blank line between groups, alphabetical within group → explicit import lists or `qualified` for non-Prelude (especially `Map`/`Set`) → hierarchical std names (`Data.List`, not legacy `List`).
**Invariant:** unqualified `Map`/`Set`, missing export list discipline, or undocumented exported API fails review.
**Probe:** stylish-haskell import check; Haddock build; grep `^import [A-Z]` without `qualified`/`(`.

## Documentation seam
**Flow:** Haddock on every exported function/type; record field comments; enough to use API without reading body.
**Invariant:** exported `foo` without `-- |` comment fails library review.
**Probe:** Haddock warnings; missing export docs audit.

## Verdict
Haddock header, camelCase names, explicit qualified imports. Learning note: `haskell-style-learning-note.md`.
