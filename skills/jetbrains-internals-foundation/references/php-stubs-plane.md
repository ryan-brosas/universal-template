<!-- capsule-v2 -->
# PHP stubs plane — how is a language's standard library shipped as typed stubs for completion/inspection?

**Source:** JetBrains IDE distributions (proprietary distribution; php stubs Apache-2.0); study/reference use only; Codebase Memory `jetbrains-phpstorm`. **Question:** How does an IDE ship the entire PHP stdlib + extensions as static typed stubs, and what metadata attributes encode language-level and availability info?

## Connected graph-selected seam
**Path/Symbol:** `phpstorm/plugins/php-impl/lib/php.jar:stubs/` — 561 files; `stubs/Core/Core.php`, plus per-extension dirs `mongodb/`(83) `swoole/`(63) `parallel/`(38) `Reflection/`(27) `solr/`(24) `rdkafka/`(22) `meta/`(22) `standard/`(16) `redis/`(4) `ldap/`(4)…
**Signature:** each stub is a valid PHP file with EMPTY function bodies + docblocks + JetBrains attributes: `#[Pure]`, `#[Deprecated]`, `#[ArrayShape]`, `#[Internal\LanguageLevelTypeAware]`, `#[Internal\PhpStormStubsElementAvailable]`.
**Data Shape:** `function zend_version(): string {}` — signature + return type + `{}` empty body; `#[Pure]` marks side-effect-free (enables dead-code analysis); `#[Internal\LanguageLevelTypeAware(["8.0"=>"int|string", "7.0"=>"string"], default="int|string")]` encodes per-PHP-version return typing; `#[PhpStormStubsElementAvailable]` gates element existence by version.

### Decisive source
```php
use JetBrains\PhpStorm\Internal\LanguageLevelTypeAware;
use JetBrains\PhpStorm\Internal\PhpStormStubsElementAvailable;
use JetBrains\PhpStorm\Pure;

/** Gets the version of the current Zend engine
 * @return string the Zend Engine version number, as a string. */
#[Pure]
function zend_version(): string {}
```

**Flow:** php.jar bundles stubs as source → IDE indexes them as the "language library" → completion/inspection/type-inference resolve symbols against these declarations → version-aware attributes let the same stub set serve multiple PHP versions → `meta/` stubs provide factory/return-type inference hints.
**Invariant:** stubs are the SOURCE OF TRUTH for the language surface — empty bodies are intentional (never executed); attributes carry the semantic payload. A porter must preserve the `#[…]` attributes or lose purity/versioning analysis.
**Probe:** `unzip -l plugins/php-impl/lib/php.jar | awk '{print $4}' | grep '^stubs/' | sed 's|stubs/||;s|/.*||' | sort | uniq -c | sort -rn | head -3` → mongodb 83 / swoole 63 / parallel 38.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm", query: "php stubs language level type aware", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: ship the language stdlib as typed stub SOURCE with empty bodies + semantic attributes (purity, deprecation, per-version typing, availability). Adapt attribute vocabulary to your host's type system. Omit the PHP corpus itself. This is the per-language twin of the spellchecker/lexicon data planes — here the "data" is compilable signature source.
